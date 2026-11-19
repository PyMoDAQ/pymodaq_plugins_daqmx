"""Typed tasks, created from a ``TaskConfig``."""
import nidaqmx
import numpy as np


class _Task:
    """What every typed task shares: a ``nidaqmx.Task`` built from a config, released on error and on close."""
    needs_timing = False

    def __init__(self, config):
        if self.needs_timing and config.timing is None:
            raise ValueError(f'{type(self).__name__} needs a timing in its configuration')
        self.config = config
        self._callbacks = []  # the driver does not keep the callbacks it is given: the task must
        self._task = nidaqmx.Task()
        try:
            for channel in config.channels:
                channel.add_to(self._task)
            if config.timing is not None:
                config.timing.apply(self._task)
            if config.trigger is not None:
                config.trigger.apply(self._task)
        except Exception:
            self._task.close()
            raise

    def on_done(self, status):
        """Called from a driver thread when the task is done. ``status`` is 0 on success. Override it."""

    def on_samples(self, data):
        """Called from a driver thread with each block of samples shaped (channels, samples). Override it."""

    def start(self, notify_every=None):
        """Start the task. With ``notify_every=n``, ``on_samples`` gets each block of n samples per channel."""
        def done(task_handle, status, callback_data):
            self.on_done(status)
            return 0

        self._callbacks.append(done)
        self._task.register_done_event(done)
        if notify_every is not None:
            self._register_samples_event(notify_every)
        self._task.start()

    def _register_samples_event(self, notify_every):
        raise NotImplementedError(f'{type(self).__name__} cannot notify about samples')

    def close(self):
        self._task.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class AnalogInputTask(_Task):
    needs_timing = True

    def read_analog(self):
        """Read the configured number of samples as a float64 array shaped (channels, samples)."""
        samples = self.config.timing.samples
        data = self._task.read(number_of_samples_per_channel=samples)
        return np.asarray(data, dtype=np.float64).reshape(len(self.config.channels), samples)

    def _register_samples_event(self, notify_every):
        def samples_acquired(task_handle, event_type, number_of_samples, callback_data):
            data = self._task.read(number_of_samples_per_channel=number_of_samples)
            self.on_samples(np.asarray(data, dtype=np.float64).reshape(len(self.config.channels), -1))
            return 0

        self._callbacks.append(samples_acquired)
        self._task.register_every_n_samples_acquired_into_buffer_event(notify_every, samples_acquired)


class AnalogOutputTask(_Task):
    def write_analog(self, data):
        """Write a DC level (scalar, single channel) or samples: 1D for one channel, 2D (channels, samples).

        A scalar is written and started at once; samples are written without starting the task.
        """
        nch = len(self.config.channels)
        if np.ndim(data) == 0:
            self._task.write(float(data), auto_start=True)
            return
        array = np.asarray(data, dtype=np.float64)
        if array.ndim == 1 and nch == 1:
            array = array.reshape(1, -1)
        if array.ndim != 2 or array.shape[0] != nch:
            raise ValueError(f'the task has {nch} channels: data must be shaped ({nch}, samples), '
                             f'got {array.shape}')
        self._task.write(array[0] if nch == 1 else array, auto_start=False)
