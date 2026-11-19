"""Typed tasks, created from a ``TaskConfig``."""
from typing import Callable, List

import nidaqmx
import numpy as np

from .config import TaskConfig


class _Task:
    """What every typed task shares: a ``nidaqmx.Task`` built from a config, released on error and on close."""
    needs_timing = False

    def __init__(self, config: TaskConfig):
        if self.needs_timing and config.timing is None:
            raise ValueError(f'{type(self).__name__} needs a timing in its configuration')
        self.config: TaskConfig = config
        self._callbacks: List[Callable] = []  # the driver does not keep the callbacks it is given: the task must
        self._task = nidaqmx.Task()
        try:
            for channel in config.channels:
                channel.add_to(self._task)
            if config.timing is not None:
                config.timing.apply_to(self._task)
            if config.trigger is not None:
                config.trigger.apply_to(self._task)
        except Exception:
            self._task.close()
            raise

    def on_done(self, status: int):
        """Called from a driver thread when the task is done. ``status`` is 0 on success. Override it."""

    def on_samples_ready(self, data: np.ndarray):
        """Called from a driver thread with each block of samples shaped (channels, samples). Override it.

        Called only if the task was started with ``start(notify_every=n)``: each block of n samples per channel is
        read in the driver callback registered by ``_register_samples_event`` (analog input tasks only for now,
        the other tasks raise ``NotImplementedError``).
        The driver runs each callback on its own thread: do not assume an order between this and ``on_done``.
        """

    def start(self, notify_every: int = None):
        """Start the task. With ``notify_every=n``, ``on_samples_ready`` gets each block of n samples per channel."""
        # the driver calls back with (task handle, status, callback_data); the last one is a user pointer
        # that we never use, the public hook is ``on_done``
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
        # same driver signature as ``done``; the public hook is ``on_samples_ready``
        def samples_acquired(task_handle, event_type, number_of_samples, callback_data):
            data = self._task.read(number_of_samples_per_channel=number_of_samples)
            self.on_samples_ready(np.asarray(data, dtype=np.float64).reshape(len(self.config.channels), -1))
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
        # a single channel takes a 1D sequence: the driver refuses a 2D array on a one-channel task
        self._task.write(array[0].tolist() if nch == 1 else array, auto_start=False)


class CounterInputTask(_Task):
    def read_counter(self, samples=None):
        """Read counter values as a float64 array shaped (counters, samples).

        ``samples`` defaults to the number of samples of the clock, or 1 when the task has no clock.
        """
        if samples is None:
            samples = getattr(self.config.timing, 'samples', None) or 1
        data = self._task.read(number_of_samples_per_channel=samples)
        return np.asarray(data, dtype=np.float64).reshape(len(self.config.channels), samples)


class CounterOutputTask(_Task):
    """Generates pulses: ``start()`` it, ``close()`` it to stop."""


class DigitalTask(_Task):
    """Reads digital input lines or drives digital output lines (not both in one task)."""

    def __init__(self, config: TaskConfig):
        from .channels import DigitalIn, DigitalOut
        kinds = {type(channel) for channel in config.channels}
        if kinds - {DigitalIn, DigitalOut}:
            raise ValueError('a DigitalTask takes DigitalIn or DigitalOut channels only')
        if len(kinds) > 1:
            raise ValueError('a DigitalTask cannot mix inputs and outputs: use one task for each')
        super().__init__(config)

    def read_digital(self, samples=1):
        """Read the levels as a boolean array shaped (lines, samples)."""
        data = self._task.read(number_of_samples_per_channel=samples)
        return np.asarray(data, dtype=np.bool_).reshape(len(self.config.channels), samples)

    def write_digital(self, levels):
        """Drive the lines now: a bool for a single line, else one bool per line."""
        nch = len(self.config.channels)
        if np.ndim(levels) == 0:
            if nch != 1:
                raise ValueError(f'the task has {nch} lines: give one level for each')
            self._task.write(bool(levels), auto_start=True)
            return
        levels = [bool(level) for level in levels]
        if len(levels) != nch:
            raise ValueError(f'the task has {nch} lines, got {len(levels)} levels')
        self._task.write(levels, auto_start=True)
