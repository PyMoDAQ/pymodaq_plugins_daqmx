"""Analog outputs of a NI device moved by voltage ramps timed by a counter used as a clock."""
import time

import numpy as np

from pymodaq_plugins_daqmx.hardware.national_instruments.daqmxni import (
    NIDAQmx, AOChannel, ClockCounter, ClockSettings, AcquisitionType)


class RampOutputController:
    """Several analog outputs sharing one clock: each voltage change is a ramp of steps of one `step_time`.

    The device gives no read-back of the voltage while a ramp is running (all the values are written to the buffer at
    once), so the voltage of each output is estimated from the time elapsed since the start of the ramp.
    """

    def __init__(self):
        self.clock = NIDAQmx()
        self.analog = NIDAQmx()
        self.axes: dict[str, AOChannel] = {}
        self.final: dict[str, float] = {}  # voltage reached at the end of the last ramp, for each axis
        self.clock_channel = ''
        self._ramp = None  # (start time, step time, {axis: values}) of the running ramp
        self._time = time.monotonic

    def configure_axis(self, axis: str, channel: str, vmin: float, vmax: float):
        self.axes[axis] = AOChannel(name=channel, value_min=vmin, value_max=vmax)
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

    def ramp(self, axis: str, voltages, step_time: float):
        """Bring one output through the successive `voltages`, one every `step_time` seconds.

        The other outputs stay where they are (where they are estimated to be if a ramp was running).
        """
        voltages = np.atleast_1d(np.asarray(voltages, dtype=float))
        for ax in self.axes:
            self.final[ax] = self.voltage(ax)
        self.stop()
        names = list(self.axes)
        values = {ax: (voltages if ax == axis else np.full(len(voltages), self.final[ax])) for ax in names}
        task_channels = [self.axes[ax] for ax in names]
        data = np.array([values[ax] for ax in names])
        if len(voltages) == 1:  # no timing needed for one value
            self.analog.update_task(task_channels, ClockSettings(Nsamples=1))
            self.analog.task.write(data[:, 0].tolist() if len(names) > 1 else float(data[0, 0]), auto_start=True)
            self.final[axis] = float(voltages[-1])
            self._ramp = None
            return
        frequency = 1 / step_time
        clock = ClockCounter(clock_frequency=frequency, name=self.clock_channel)
        self.clock.update_task([clock], ClockSettings(Nsamples=1))
        self.clock.task.timing.cfg_implicit_timing(sample_mode=AcquisitionType.FINITE,
                                                   samps_per_chan=len(voltages) + 1)
        self.analog.update_task(task_channels, ClockSettings(Nsamples=1))
        self.analog.task.timing.cfg_samp_clk_timing(frequency, source='/' + self.clock_channel + 'InternalOutput',
                                                    sample_mode=AcquisitionType.FINITE,
                                                    samps_per_chan=len(voltages))
        self.analog.task.write(data.tolist() if len(names) > 1 else data[0].tolist(), auto_start=False)
        self.analog.task.start()
        self.clock.task.start()
        self._ramp = (self._time(), step_time, values)
        self.final[axis] = float(voltages[-1])

    def stop(self):
        """Stop the ramp, the outputs keep the voltage they have reached."""
        if self._ramp is not None:
            for ax in self.axes:
                self.final[ax] = self.voltage(ax)
            self._ramp = None
        self.clock.stop()
        self.analog.stop()

    def close(self):
        self.stop()
        self.clock.close()
        self.analog.close()
