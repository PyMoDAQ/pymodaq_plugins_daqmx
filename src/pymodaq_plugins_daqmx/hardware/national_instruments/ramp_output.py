"""Analog outputs of a NI device moved by voltage ramps timed by a counter used as a clock."""
import time

import numpy as np

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AOVoltage, AnalogOutputTask, COPulseFreq, ClockSettings, CounterOutputTask, ImplicitTiming, TaskConfig,
    TaskGroup, counter_output_terminal)


class RampOutputController:
    """Several analog outputs sharing one clock: each voltage change is a ramp of steps of one `step_time`.

    The device gives no read-back of the voltage while a ramp is running (all the values are written to the buffer at
    once), so the voltage of each output is estimated from the time elapsed since the start of the ramp.
    """

    def __init__(self):
        self.clock: CounterOutputTask = None  # the tasks of the running ramp, replaced at each ramp
        self.analog: AnalogOutputTask = None
        self.group: TaskGroup = None  # the analog outputs, armed first, and the clock that times them
        self.axes: dict[str, AOVoltage] = {}
        self.final: dict[str, float] = {}  # voltage reached at the end of the last ramp, for each axis
        self.clock_channel = ''
        self._ramp = None  # (start time, step time, {axis: values}) of the running ramp
        self._time = time.monotonic

    def configure_axis(self, axis: str, channel: str, vmin: float, vmax: float):
        self.axes[axis] = AOVoltage(channel, min_val=vmin, max_val=vmax)
        self.final.setdefault(axis, 0.)

    def voltage(self, axis: str) -> float:
        """Voltage of the output, as estimated from the elapsed time if a ramp is running."""
        if self._ramp is None:
            return self.final[axis]
        t0, step_time, values = self._ramp
        if axis not in values:
            return self.final[axis]
        index = min(int((self._time() - t0) / step_time), len(values[axis]) - 1)
        return float(values[axis][max(index, 0)])

    def is_moving(self) -> bool:
        if self._ramp is None:
            return False
        t0, step_time, values = self._ramp
        n = len(next(iter(values.values())))
        return self._time() - t0 < n * step_time

    def _pending(self) -> dict:
        """What the running ramp has still to do, for each axis: the values not yet applied."""
        if self._ramp is None:
            return {}
        t0, step_time, values = self._ramp
        n = len(next(iter(values.values())))
        index = max(min(int((self._time() - t0) / step_time), n - 1), 0)
        return {ax: vals[index:] for ax, vals in values.items()}

    def ramp(self, axis: str, voltages, step_time: float):
        """Bring one output through the successive `voltages`, one every `step_time` seconds.

        The other outputs stay where they are, or carry on towards their target if their ramp is still running: the
        remaining steps are restarted together with the new ramp, so that axes moved one just after the other (the
        Scan extension does it) all reach their targets.
        """
        voltages = np.atleast_1d(np.asarray(voltages, dtype=float))
        pending = self._pending()
        for ax in self.axes:
            self.final[ax] = self.voltage(ax)
        self.stop()
        names = list(self.axes)
        sequences = {ax: (voltages if ax == axis else np.asarray(pending.get(ax, [self.final[ax]]), dtype=float))
                     for ax in names}
        n = max(len(seq) for seq in sequences.values())
        values = {ax: np.concatenate([seq, np.full(n - len(seq), seq[-1])]) for ax, seq in sequences.items()}
        voltages = values[axis]
        task_channels = [self.axes[ax] for ax in names]
        data = np.array([values[ax] for ax in names])
        self._release()  # the outputs are free for the tasks of this ramp
        if len(voltages) == 1:  # no timing needed for one value
            self.analog = AnalogOutputTask(TaskConfig(channels=task_channels))
            self.analog.write_levels(data[:, 0])
            self.final.update({ax: float(vals[-1]) for ax, vals in values.items()})
            self._ramp = None
            return
        frequency = 1 / step_time
        self.clock = CounterOutputTask(TaskConfig(
            channels=[COPulseFreq(self.clock_channel, frequency=frequency)],
            timing=ImplicitTiming(samples=len(voltages) + 1)))
        self.analog = AnalogOutputTask(TaskConfig(
            channels=task_channels,
            timing=ClockSettings(rate=frequency, samples=len(voltages),
                                 source=counter_output_terminal(self.clock_channel))))
        self.analog.write_analog(data)
        self.group = TaskGroup(self.analog, self.clock)
        self.group.start()
        self._ramp = (self._time(), step_time, values)
        self.final.update({ax: float(vals[-1]) for ax, vals in values.items()})

    def stop(self):
        """Stop the ramp, the outputs keep the voltage they have reached."""
        if self._ramp is not None:
            for ax in self.axes:
                self.final[ax] = self.voltage(ax)
            self._ramp = None
        if self.group is not None:
            self.group.stop()
        elif self.analog is not None:
            self.analog.stop()

    def _release(self):
        """Close the tasks of the last ramp. They stay open after a ramp, which keeps the outputs where they are."""
        if self.group is not None:
            self.group.close()
        elif self.analog is not None:
            self.analog.close()
        self.clock = self.analog = self.group = None

    def close(self):
        self.stop()
        self._release()
