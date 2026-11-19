"""A stand-in for the ``nidaqmx`` package, placed at the external boundary of the public API.

Its behaviour copies what ``tests/contract/contract_check.py`` recorded on NI MAX simulated devices
(nidaqmx 1.7.0): the shape returned by ``task.read`` depends on the number of channels and samples,
and every driver error is a ``nidaqmx.DaqError`` carrying an ``error_code``.
"""
import threading
import weakref

import nidaqmx
import pytest


KNOWN_COUNTERS = {f"Dev2/ctr{c}" for c in range(4)}
KNOWN_AO_CHANNELS = {f"Dev2/ao{c}" for c in range(4)}
KNOWN_LINES = {f"Dev2/port0/line{c}" for c in range(8)}
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


class _CounterChannels:
    def __init__(self, task):
        self._task = task

    def _add(self, kind, counter, **settings):
        if counter not in KNOWN_COUNTERS:
            raise nidaqmx.DaqError('Physical channel specified does not exist on this device.', -200170)
        self._task.channels.append((kind, counter, settings))

    def add_ci_count_edges_chan(self, counter, name_to_assign_to_channel="", edge=None, initial_count=0,
                                count_direction=None):
        self._add('ci_count_edges', counter, edge=edge, initial_count=initial_count,
                  count_direction=count_direction)

    def add_ci_semi_period_chan(self, counter, name_to_assign_to_channel="", min_val=0.0, max_val=1.0,
                                units=None, custom_scale_name=None):
        self._add('ci_semi_period', counter, min_val=min_val, max_val=max_val, units=units)

    def add_co_pulse_chan_freq(self, counter, name_to_assign_to_channel="", units=None, idle_state=None,
                               initial_delay=0.0, freq=1.0, duty_cycle=0.5):
        self._add('co_pulse_freq', counter, freq=freq, duty_cycle=duty_cycle, idle_state=idle_state,
                  initial_delay=initial_delay)


class _DigitalChannels:
    def __init__(self, task):
        self._task = task

    def _add(self, kind, lines, line_grouping):
        if lines not in KNOWN_LINES:
            raise nidaqmx.DaqError('Physical channel specified does not exist on this device.', -200170)
        self._task.channels.append((kind, lines, dict(line_grouping=line_grouping)))

    def add_di_chan(self, lines, name_to_assign_to_lines="", line_grouping=None):
        self._add('di', lines, line_grouping)

    def add_do_chan(self, lines, name_to_assign_to_lines="", line_grouping=None):
        self._add('do', lines, line_grouping)


class _Timing:
    def __init__(self, task):
        self._task = task

    def cfg_implicit_timing(self, sample_mode=None, samps_per_chan=1000):
        self._task.timing_calls.append(('implicit', sample_mode, samps_per_chan))

    def cfg_change_detection_timing(self, rising_edge_chan="", falling_edge_chan="", sample_mode=None,
                                    samps_per_chan=1000):
        self._task.timing_calls.append(('change_detection', rising_edge_chan, falling_edge_chan,
                                        sample_mode, samps_per_chan))

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

    edges_per_sample = 0  # edges a counter input sees between two samples; tests set it with monkeypatch

    def __init__(self, new_task_name=""):
        self.channels = []
        self.timing_calls = []
        self.trigger_calls = []
        self.closed = False
        self.started = False
        self.starts = 0
        self.stops = 0
        self.read_timeouts = []
        self.callback_threads = []
        self.ai_channels = _Channels(self)
        self.ao_channels = _AOChannels(self)
        self.di_channels = self.do_channels = _DigitalChannels(self)
        self.ci_channels = self.co_channels = _CounterChannels(self)
        self.writes = []
        self.timing = _Timing(self)
        self.triggers = _Triggers(self)

    def read(self, number_of_samples_per_channel=None, timeout=10.0):
        n = number_of_samples_per_channel
        self.read_timeouts.append(timeout)
        nch = len(self.channels)
        # values are chosen so that channel c, sample s reads c + s / 10
        if self.channels and self.channels[0][0] == 'ci_count_edges' and self.edges_per_sample:
            # an invented signal (the simulated devices count nothing): sample s holds the edges counted so far
            rows = [[self.edges_per_sample * (s + 1) for s in range(n)] for c in range(nch)]
            return rows[0] if nch == 1 else rows
        if self.channels and self.channels[0][0] == 'di':
            # digital lines read booleans: line c, sample s is high when c + s is even
            rows = [[(c + s) % 2 == 0 for s in range(n)] for c in range(nch)]
            return rows[0] if nch == 1 else rows
        rows = [[c + s / 10 for s in range(n)] for c in range(nch)]
        return rows[0] if nch == 1 else rows

    def write(self, data, auto_start=False, timeout=10.0):
        """Like nidaqmx: the data must hold one row per channel; returns the samples written per channel."""
        import numpy as np
        if self.channels and self.channels[0][0] == 'do':
            self.writes.append((data, auto_start))
            return 1  # recorded: write returns the number of samples written
        array = np.asarray(data, dtype=float)
        nch = len(self.channels)
        if nch == 1 and array.ndim == 2:
            # recorded on a PCIe-6363 (contract_report_Dev2.json): a one-channel task accepts a python list or
            # a 1D numpy array, and refuses a 2D numpy array, whether shaped (1, N) or (N, 1)
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
        self.starts += 1

    def stop(self):
        self.stops += 1
        self.started = False

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


class _Names:
    def __init__(self, names):
        self.channel_names = list(names)
        self.device_names = list(names)

    def __iter__(self):
        return iter(self.channel_names)


def _flat(ranges):
    return [value for pair in ranges for value in pair]


class DoubleDevice:
    """Values copied from the reports of a PCIe-6363 (``Dev2``) and of a PCI-6133 without analog output."""

    def __init__(self, name, **properties):
        self.name = name
        self._properties = properties

    def _get(self, key):
        value = self._properties[key]
        if isinstance(value, Exception):
            raise value
        return value

    ai_physical_chans = property(lambda self: _Names(self._get('ai')))
    ao_physical_chans = property(lambda self: _Names(self._get('ao')))
    ci_physical_chans = property(lambda self: _Names(self._get('ci')))
    co_physical_chans = property(lambda self: _Names(self._get('co')))
    di_lines = property(lambda self: _Names(self._get('di')))
    do_lines = property(lambda self: _Names(self._get('do')))
    terminals = property(lambda self: self._get('terminals'))
    ai_voltage_rngs = property(lambda self: _flat(self._get('ai_ranges')))
    ao_voltage_rngs = property(lambda self: _flat(self._get('ao_ranges')))
    ai_max_multi_chan_rate = property(lambda self: self._get('ai_max_multi'))
    ai_max_single_chan_rate = property(lambda self: self._get('ai_max_single'))
    ao_max_rate = property(lambda self: self._get('ao_max'))
    ai_trig_usage = property(lambda self: self._get('ai_trig'))
    di_trig_usage = property(lambda self: self._get('di_trig'))


def _pcie_6363():
    from nidaqmx.constants import TriggerUsage
    start_pause_reference = [TriggerUsage.PAUSE, TriggerUsage.REFERENCE, TriggerUsage.START]
    return DoubleDevice(
        'Dev2', ai=[f'Dev2/ai{c}' for c in range(32)], ao=[f'Dev2/ao{c}' for c in range(4)],
        ci=[f'Dev2/ctr{c}' for c in range(4)], co=[f'Dev2/ctr{c}' for c in range(4)] + ['Dev2/freqout'],
        di=[f'Dev2/port0/line{c}' for c in range(4)], do=[f'Dev2/port0/line{c}' for c in range(4)],
        terminals=[f'/Dev2/PFI{c}' for c in range(6)],
        ai_ranges=[(-0.1, 0.1), (-0.2, 0.2), (-0.5, 0.5), (-1.0, 1.0), (-2.0, 2.0), (-5.0, 5.0), (-10.0, 10.0)],
        ao_ranges=[(-5.0, 5.0), (-10.0, 10.0)], ai_max_multi=1000000.0, ai_max_single=2000000.0,
        ao_max=2857142.8571428573, ai_trig=start_pause_reference, di_trig=start_pause_reference)


def _pci_6133():
    from nidaqmx.constants import TriggerUsage
    return DoubleDevice(
        'Dev1', ai=[f'Dev1/ai{c}' for c in range(8)], ao=[], ci=['Dev1/ctr0', 'Dev1/ctr1'],
        co=['Dev1/ctr0', 'Dev1/ctr1', 'Dev1/freqout'], di=[f'Dev1/port0/line{c}' for c in range(4)],
        do=[f'Dev1/port0/line{c}' for c in range(4)], terminals=[f'/Dev1/PFI{c}' for c in range(6)],
        ai_ranges=[(-1.25, 1.25), (-2.5, 2.5), (-5.0, 5.0), (-10.0, 10.0)], ao_ranges=[],
        ai_max_multi=2500000.0, ai_max_single=2500000.0,
        ao_max=nidaqmx.DaqError('Device does not support this property.', -200197),
        ai_trig=[TriggerUsage.PAUSE, TriggerUsage.REFERENCE, TriggerUsage.START], di_trig=[])


class DoubleSystem:
    """What ``nidaqmx.system.System`` gives: ``local()`` is the driver, which may be missing."""
    installed_devices = None   # set by the fixture
    driver_present = True

    @classmethod
    def local(cls):
        if not cls.driver_present:
            raise nidaqmx.errors.DaqNotFoundError(
                'Could not find an installation of NI-DAQmx. Please ensure that NI-DAQmx is installed on this '
                'machine or contact National Instruments for support.')
        return cls()

    @property
    def devices(self):
        return _DevicesCollection(self.installed_devices)


class _DevicesCollection(_Names):
    def __init__(self, devices):
        super().__init__([device.name for device in devices])
        self._devices = {device.name: device for device in devices}

    def __getitem__(self, name):
        return self._devices[name]


@pytest.fixture
def system_driver(monkeypatch):
    """Replace ``nidaqmx.system.System`` by one with a PCI-6133 (Dev1) and a PCIe-6363 (Dev2)."""
    import nidaqmx.system
    DoubleSystem.installed_devices = [_pci_6133(), _pcie_6363()]
    DoubleSystem.driver_present = True
    monkeypatch.setattr(nidaqmx.system, 'System', DoubleSystem)
    return DoubleSystem
