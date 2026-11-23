"""Plays arrays of samples on several analog outputs of one NI device, with one task (one clock, one trigger)."""
from typing import Callable, Optional, Sequence

import numpy as np
from pymodaq.utils.logger import get_module_name, set_logger
from pymodaq_plugins_utils.hardware.waveform_output import OutputMode

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AOVoltage, AnalogOutputTask, ClockSettings, TaskConfig)
from pymodaq_plugins_daqmx.hardware.national_instruments.qt_task_bridge import QtTaskBridge

logger = set_logger(get_module_name(__file__))


class WaveformPlayer:
    """The analog outputs ``channels`` (all of the same device: a NI task cannot span several), driven by one task.

    Between two waveforms (and before the first) the outputs are held at 0 V by a task without clock. A waveform is
    played by a new task, the previous one being closed: there is no seamless update, the outputs go through 0 V
    between two waveforms (the capability ``live_update`` of the plugin is False). When a finite waveform ends, its
    task stays open so that the outputs keep the last sample until the next waveform, ``park`` or ``close``.
    """

    def __init__(self, channels: Sequence[AOVoltage]):
        if not channels:
            raise ValueError('no analog output chosen')
        devices = {channel.name.partition('/')[0] for channel in channels}
        if len(devices) > 1:
            raise ValueError(f'the outputs of one task belong to one device, got {", ".join(sorted(devices))}')
        self.channels = list(channels)
        self.task: Optional[AnalogOutputTask] = None
        self.bridge: Optional[QtTaskBridge] = None
        self.playing = False  # a waveform is being generated (a continuous one until stopped)

    @property
    def n_channels(self) -> int:
        return len(self.channels)

    def play(self, samples: np.ndarray, rate: float, mode: OutputMode, repetitions: int = 1, clock_source: str = '',
             trigger=None, on_done: Optional[Callable[[int], None]] = None) -> None:
        """Generate ``samples`` (volts, one row per channel) at ``rate`` Hz, in the ``mode`` of the output.

        ``on_done(status)`` is called, in the thread that calls ``play`` (it needs an event loop), when a finite
        or repeated generation has ended: status 0, or the code of the driver error. It is not called for a
        continuous generation. Must be called from the thread of the plugin.
        """
        samples = np.asarray(samples, dtype=float)
        if samples.ndim != 2 or samples.shape[0] != self.n_channels:
            raise ValueError(f'{self.n_channels} channels: the samples should be shaped ({self.n_channels}, N), '
                             f'got {samples.shape}')
        mode = OutputMode(mode)
        n = samples.shape[1]
        if mode == OutputMode.FINITE:
            data, timing = samples, ClockSettings(rate, samples=n, source=clock_source)
        elif mode == OutputMode.REPEAT:
            data = np.tile(samples, (1, int(repetitions)))
            timing = ClockSettings(rate, samples=data.shape[1], source=clock_source)
        else:  # the driver repeats the buffer: its size is the signal
            data, timing = samples, ClockSettings(rate, buffer=n, source=clock_source)
        self._release()
        task = AnalogOutputTask(TaskConfig(channels=self.channels, timing=timing, trigger=trigger))
        try:
            task.write_analog(data)
            if on_done is not None and mode != OutputMode.CONTINUOUS:
                self.bridge = QtTaskBridge(task)
                self.bridge.done.connect(lambda status: self._ended(status, on_done))
            task.start()
        except Exception:
            self._close_task(task)
            self.bridge = None
            raise
        self.task, self.playing = task, True

    def _ended(self, status: int, on_done: Callable[[int], None]) -> None:
        self.playing = False
        on_done(status)

    def park(self) -> None:
        """Stop what is played and hold every output at 0 V."""
        self._release()
        self.task = AnalogOutputTask(TaskConfig(channels=self.channels))
        self.task.write_levels([0.] * self.n_channels)

    def close(self) -> None:
        """Set the outputs to 0 V and release them (the channels are only this task's while it is open)."""
        try:
            self.park()
        except Exception:  # closing must go on: the channels have to be released
            logger.warning('The outputs could not be set to 0 V', exc_info=True)
        self._release()

    def _release(self) -> None:
        self.playing = False
        if self.bridge is not None:
            self.bridge.close()
            self.bridge = None
        if self.task is not None:
            self._close_task(self.task)
            self.task = None

    @staticmethod
    def _close_task(task: AnalogOutputTask) -> None:
        try:
            task.stop()
        finally:
            task.close()
