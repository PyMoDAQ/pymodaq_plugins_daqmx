"""A stand-in for the ``nidaqmx`` package, placed at the external boundary of the public API.

Its behaviour copies what ``tests/contract/contract_check.py`` recorded on NI MAX simulated devices
(nidaqmx 1.7.0): the shape returned by ``task.read`` depends on the number of channels and samples,
and every driver error is a ``nidaqmx.DaqError`` carrying an ``error_code``.
"""
import threading
import weakref

import nidaqmx
import pytest


KNOWN_AO_CHANNELS = {f"Dev2/ao{c}" for c in range(4)}
KNOWN_AI_CHANNELS = {f"Dev{d}/ai{c}" for d in (1, 2) for c in range(8)}


class _Channels:
    def __init__(self, task):
        self._task = task

    def _add(self, kind, physical_channel, **settings):
        if physical_channel not in KNOWN_AI_CHANNELS:
            raise nidaqmx.DaqError('Physical channel specified does not exist on this device.', -200170)
        self._task.channels.append((kind, physical_channel, settings))

    def add_ai_voltage_chan(self, physical_channel, name_to_assign_to_channel="", terminal_config=None,
                            min_val=-5.0, max_val=5.0, units=None, custom_scale_name=None):
        self._add('ai_voltage', physical_channel, terminal_config=terminal_config,
                  min_val=min_val, max_val=max_val)

    def add_ai_current_chan(self, physical_channel, name_to_assign_to_channel="", terminal_config=None,
                            min_val=-0.02, max_val=0.02, units=None, shunt_resistor_loc=None,
                            ext_shunt_resistor_val=249.0, custom_scale_name=None):
        self._add('ai_current', physical_channel, terminal_config=terminal_config,
                  min_val=min_val, max_val=max_val)

    def add_ai_thrmcpl_chan(self, physical_channel, name_to_assign_to_channel="", min_val=0.0,
                            max_val=100.0, units=None, thermocouple_type=None, cjc_source=None,
                            cjc_val=25.0, cjc_channel=""):
        self._add('ai_thermocouple', physical_channel, min_val=min_val, max_val=max_val, units=units,
                  thermocouple_type=thermocouple_type)

    def add_ai_rtd_chan(self, physical_channel, name_to_assign_to_channel="", min_val=0.0, max_val=100.0,
                        units=None, rtd_type=None, resistance_config=None, current_excit_source=None,
                        current_excit_val=0.0025, r_0=100.0):
        self._add('ai_rtd', physical_channel, min_val=min_val, max_val=max_val, units=units,
                  rtd_type=rtd_type, resistance_config=resistance_config,
                  current_excit_source=current_excit_source, current_excit_val=current_excit_val, r_0=r_0)


class _AOChannels:
    def __init__(self, task):
        self._task = task

    def _add(self, kind, physical_channel, **settings):
        if physical_channel not in KNOWN_AO_CHANNELS:
            raise nidaqmx.DaqError('Physical channel specified does not exist on this device.', -200170)
        self._task.channels.append((kind, physical_channel, settings))

    def add_ao_voltage_chan(self, physical_channel, name_to_assign_to_channel="", min_val=-5.0, max_val=5.0,
                            units=None, custom_scale_name=None):
        self._add('ao_voltage', physical_channel, min_val=min_val, max_val=max_val)

    def add_ao_current_chan(self, physical_channel, name_to_assign_to_channel="", min_val=0.0, max_val=0.02,
                            units=None, custom_scale_name=None):
        self._add('ao_current', physical_channel, min_val=min_val, max_val=max_val)


class _Timing:
    def __init__(self, task):
        self._task = task

    def cfg_samp_clk_timing(self, rate, source="", active_edge=None, sample_mode=None, samps_per_chan=1000):
        self._task.timing_calls.append(('samp_clk', rate, dict(
            source=source, active_edge=active_edge, sample_mode=sample_mode, samps_per_chan=samps_per_chan)))


class _StartTrigger:
    def __init__(self, task):
        self._task = task

    def cfg_dig_edge_start_trig(self, trigger_source, trigger_edge=None):
        self._task.trigger_calls.append(('dig_edge', trigger_source, trigger_edge))

    def cfg_anlg_edge_start_trig(self, trigger_source="", trigger_slope=None, trigger_level=0.0):
        self._task.trigger_calls.append(('anlg_edge', trigger_source, trigger_slope, trigger_level))


class _Triggers:
    def __init__(self, task):
        self.start_trigger = _StartTrigger(task)


class DoubleTask:
    """What ``nidaqmx.Task`` does, without driver nor hardware."""

    def __init__(self, new_task_name=""):
        self.channels = []
        self.timing_calls = []
        self.trigger_calls = []
        self.closed = False
        self.started = False
        self.callback_threads = []
        self.ai_channels = _Channels(self)
        self.ao_channels = _AOChannels(self)
        self.writes = []
        self.timing = _Timing(self)
        self.triggers = _Triggers(self)

    def read(self, number_of_samples_per_channel=None, timeout=10.0):
        n = number_of_samples_per_channel
        nch = len(self.channels)
        # values are chosen so that channel c, sample s reads c + s / 10
        rows = [[c + s / 10 for s in range(n)] for c in range(nch)]
        return rows[0] if nch == 1 else rows

    def write(self, data, auto_start=False, timeout=10.0):
        """Like nidaqmx: the data must hold one row per channel; returns the samples written per channel."""
        import numpy as np
        array = np.asarray(data, dtype=float)
        nch = len(self.channels)
        if nch == 1 and isinstance(data, np.ndarray):
            # recorded on a PCIe-6363 (contract_report_Dev2.json): a numpy array written to a one-channel
            # task was refused with -200524, whereas a plain list was accepted. Which of the 1D and the
            # (1, N) array was refused is not known yet, so both are refused here: pass a list.
            raise nidaqmx.DaqError('Write cannot be performed, because the number of channels in the data '
                                   'does not match the number of channels in the task.', -200524)
        if nch > 1 and (array.ndim != 2 or array.shape[0] != nch):
            raise nidaqmx.DaqError('Write cannot be performed, because the number of channels in the data '
                                   'does not match the number of channels in the task.', -200524)
        self.writes.append((array.tolist(), auto_start))
        return 1 if array.ndim == 0 else array.shape[-1]

    def register_every_n_samples_acquired_into_buffer_event(self, sample_interval, callback_method):
        # like a C driver, hold the callback weakly: whoever registers it must keep it alive
        self._every_n = (sample_interval, weakref.ref(callback_method))

    def register_done_event(self, callback_method):
        self._done = weakref.ref(callback_method)

    def _call_from_driver_thread(self, callback, *args):
        """The driver calls back from a thread of its own, never from the caller's thread."""
        callback = callback()
        assert callback is not None, 'the callback was garbage collected: nobody kept a reference'
        result = []
        thread = threading.Thread(target=lambda: result.append(callback(*args)), name='driver')
        thread.start()
        thread.join()
        self.callback_threads.append(thread.name)
        return result[0]

    def fire_samples(self):
        """The driver has acquired another block of samples."""
        interval, callback = self._every_n
        return self._call_from_driver_thread(callback, 1234, 1, interval, None)

    def fire_done(self, status=0):
        return self._call_from_driver_thread(self._done, 1234, status, None)

    def start(self):
        self.started = True

    def stop(self):
        pass

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


@pytest.fixture
def driver(monkeypatch):
    """Replace the driver boundary: ``nidaqmx.Task`` becomes a ``DoubleTask``."""
    created = []

    def make(*args, **kwargs):
        task = DoubleTask(*args, **kwargs)
        created.append(task)
        return task

    monkeypatch.setattr(nidaqmx, 'Task', make)
    return created
