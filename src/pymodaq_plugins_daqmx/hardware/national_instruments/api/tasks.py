"""Typed tasks, created from a ``TaskConfig``."""
import nidaqmx
import numpy as np


class AnalogInputTask:
    def __init__(self, config):
        self.config = config
        self._task = nidaqmx.Task()
        for channel in config.channels:
            channel.add_to(self._task)
        config.timing.apply(self._task)

    def read_analog(self):
        """Read the configured number of samples as a float64 array shaped (channels, samples)."""
        samples = self.config.timing.samples
        data = self._task.read(number_of_samples_per_channel=samples)
        return np.asarray(data, dtype=np.float64).reshape(len(self.config.channels), samples)

    def close(self):
        self._task.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
