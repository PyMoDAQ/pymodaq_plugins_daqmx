"""A fake of the ``NIDAQmx`` wrapper: records the configuration and returns a value read per channel."""
import numpy as np
from nidaqmx.constants import ChannelType


class FakeTiming:
    def __init__(self):
        self.calls = []

    def cfg_samp_clk_timing(self, rate, **kwargs):
        self.calls.append(('cfg_samp_clk_timing', rate, kwargs))

    def cfg_implicit_timing(self, **kwargs):
        self.calls.append(('cfg_implicit_timing', kwargs))


class FakeTask:
    def __init__(self, owner):
        self.owner = owner
        self.running = False
        self.timing = FakeTiming()
        self.started = 0

    def start(self):
        self.running = True
        self.started += 1

    def stop(self):
        self.running = False

    def write(self, data, auto_start=False):
        self.owner.writes.append((data, auto_start))

    def read(self, number_of_samples_per_channel=1, timeout=10.):
        self.owner.reads.append((number_of_samples_per_channel, timeout))
        if self.owner.channels and self.owner.channels[0].source == ChannelType.COUNTER_INPUT:
            return self.owner.counts
        nchan = len(self.owner.channels)
        data = [np.full(number_of_samples_per_channel, float(i + 1)) for i in range(nchan)]
        if nchan == 1:
            return data[0].tolist()
        return [d.tolist() for d in data]


class FakeNIDAQmx:
    """Stands for ``daqmxni.NIDAQmx`` (the nidaqmx wrapper)."""

    counts = 50  # edges seen by a counter during one counting time

    def __init__(self):
        self.channels = []
        self.clock = None
        self.reads = []
        self.writes = []
        self.closed = False
        self._task = None

    @classmethod
    def get_NIDAQ_channels(cls, devices=None, source_type=None):
        return ['Dev1/ai0', 'Dev1/ai1', 'Dev1/ai2', 'Dev1/ai3']

    @property
    def task(self):
        return self._task

    def update_task(self, channels=(), clock_settings=None, trigger_settings=None):
        self.channels = list(channels)
        self.clock = clock_settings
        self._task = FakeTask(self)

    def stop(self):
        if self._task is not None:
            self._task.stop()

    def close(self):
        self.closed = True
        self._task = None
