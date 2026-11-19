"""A stand-in for the ``nidaqmx`` package, placed at the external boundary of the public API.

Its behaviour copies what ``tests/contract/contract_check.py`` recorded on NI MAX simulated devices
(nidaqmx 1.7.0): the shape returned by ``task.read`` depends on the number of channels and samples,
and every driver error is a ``nidaqmx.DaqError`` carrying an ``error_code``.
"""
import nidaqmx
import pytest


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
        self.ai_channels = _Channels(self)
        self.timing = _Timing(self)
        self.triggers = _Triggers(self)

    def read(self, number_of_samples_per_channel=None, timeout=10.0):
        n = number_of_samples_per_channel
        nch = len(self.channels)
        # values are chosen so that channel c, sample s reads c + s / 10
        rows = [[c + s / 10 for s in range(n)] for c in range(nch)]
        return rows[0] if nch == 1 else rows

    def start(self):
        pass

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
