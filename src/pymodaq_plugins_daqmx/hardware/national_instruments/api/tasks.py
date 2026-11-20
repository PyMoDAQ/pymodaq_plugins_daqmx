"""Typed tasks, created from a ``TaskConfig``."""
from typing import Callable, List, Optional, Sequence, Union

import nidaqmx
import numpy as np

from .config import TaskConfig


class TaskListener:
    """What a task can tell: derive from it and register the object with ``task.add_listener``.

    Both methods are called from driver threads, never from the thread that started the task, one thread per call
    and without any order between them. Do only what is thread-safe here, or hand the event over to the thread
    that should handle it (see ``QtTaskBridge``).
    """

    def on_samples_ready(self, data: np.ndarray):
        """A block of samples shaped (channels, samples); only if the task was started with ``notify_every=n``."""

    def on_done(self, status: int):
        """The task is done. ``status`` is 0 on success, else a driver error code."""


class _Task:
    """What every typed task shares: a ``nidaqmx.Task`` built from a config, released on error and on close."""
    needs_timing = False

    def __init__(self, config: TaskConfig):
        if self.needs_timing and config.timing is None:
            raise ValueError(f'{type(self).__name__} needs a timing in its configuration')
        self.config: TaskConfig = config
        self._listeners: List[TaskListener] = []
        self._callbacks: List[Callable] = []  # the driver does not keep the callbacks it is given: the task must
        self._done_registered = False
        self._samples_interval: Optional[int] = None  # block size of the registered samples event, if any
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

    def add_listener(self, listener: TaskListener):
        """Tell ``listener`` (a `TaskListener`) about the blocks of samples and the end of the task."""
        self._listeners.append(listener)

    def remove_listener(self, listener: TaskListener):
        self._listeners.remove(listener)

    def on_done(self, status: int):
        """Called from a driver thread when the task is done. ``status`` is 0 on success. Override it, or better,
        register a `TaskListener`."""

    def on_samples_ready(self, data: np.ndarray):
        """Called from a driver thread with each block of samples shaped (channels, samples). Override it, or
        better, register a `TaskListener`.

        Called only if the task was started with ``start(notify_every=n)``: each block of n samples per channel is
        read in the driver callback registered by ``_register_samples_event`` (analog input tasks only for now,
        the other tasks raise ``NotImplementedError``).
        The driver runs each callback on its own thread: do not assume an order between this and ``on_done``.
        """

    def start(self, notify_every: int = None):
        """Start the task. With ``notify_every=n``, ``on_samples_ready`` gets each block of n samples per channel.

        The task can be started again after ``stop()``, with another ``notify_every``.
        """
        self._register_done_event()
        if notify_every != self._samples_interval:
            self._set_samples_event(notify_every)
        self._task.start()

    def _register_done_event(self):
        if self._done_registered:  # the driver refuses to register an event twice
            return

        # the driver calls back with (task handle, status, callback_data); the last one is a user pointer
        # that we never use, the public hook is ``on_done``
        def done(task_handle, status, callback_data):
            self.on_done(status)
            for listener in list(self._listeners):
                listener.on_done(status)
            return 0

        self._callbacks.append(done)
        self._task.register_done_event(done)
        self._done_registered = True

    def _set_samples_event(self, notify_every):
        if self._samples_interval is not None:
            self._unregister_samples_event(self._samples_interval)
            self._samples_interval = None
        if notify_every is not None:
            self._register_samples_event(notify_every)
            self._samples_interval = notify_every

    def _unregister_samples_event(self, interval):
        self._task.register_every_n_samples_acquired_into_buffer_event(interval, None)

    def _register_samples_event(self, notify_every):
        raise NotImplementedError(f'{type(self).__name__} cannot notify about samples')

    def stop(self):
        """Stop the task, which can then be started again."""
        self._task.stop()

    def close(self):
        self._task.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class AnalogInputTask(_Task):
    needs_timing = True

    def read_analog(self, timeout: Optional[float] = None) -> np.ndarray:
        """Read the configured number of samples as a float64 array shaped (channels, samples).

        ``timeout`` (s) is how long to wait for the samples: by default the duration of the acquisition plus 5 s.
        """
        samples = self.config.timing.samples
        if samples is None:
            raise ValueError('a continuous acquisition cannot be read in one go: use start(notify_every=n) '
                             'and on_samples_ready')
        if timeout is None:
            timeout = samples / self.config.timing.rate + 5.
        data = self._task.read(number_of_samples_per_channel=samples, timeout=timeout)
        return np.asarray(data, dtype=np.float64).reshape(len(self.config.channels), samples)

    def _register_samples_event(self, notify_every):
        # same driver signature as ``done``; the public hook is ``on_samples_ready``
        def samples_acquired(task_handle, event_type, number_of_samples, callback_data):
            data = self._task.read(number_of_samples_per_channel=number_of_samples)
            block = np.asarray(data, dtype=np.float64).reshape(len(self.config.channels), -1)
            self.on_samples_ready(block)
            for listener in list(self._listeners):
                listener.on_samples_ready(block)
            return 0

        self._callbacks.append(samples_acquired)
        self._task.register_every_n_samples_acquired_into_buffer_event(notify_every, samples_acquired)


class AnalogOutputTask(_Task):
    def write_analog(self, data: Union[float, Sequence[float], np.ndarray]) -> None:
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


    def write_levels(self, levels: Sequence[float]) -> None:
        """Set every output to a DC level at once, and start the task.

        ``levels`` holds one level (volts or amperes) per channel, in the order of the channels of the task.
        """
        nch = len(self.config.channels)
        levels = [float(level) for level in levels]
        if len(levels) != nch:
            raise ValueError(f'the task has {nch} channels: give {nch} levels, got {len(levels)}')
        if nch == 1:
            self._task.write(levels[0], auto_start=True)
        else:
            self._task.write(np.array(levels).reshape(nch, 1), auto_start=True)


class CounterInputTask(_Task):
    def read_counter(self, samples: Optional[int] = None) -> np.ndarray:
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

    def read_digital(self, samples: int = 1) -> np.ndarray:
        """Read the levels as a boolean array shaped (lines, samples)."""
        data = self._task.read(number_of_samples_per_channel=samples)
        return np.asarray(data, dtype=np.bool_).reshape(len(self.config.channels), samples)

    def write_digital(self, levels: Union[bool, Sequence[bool]]) -> None:
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
