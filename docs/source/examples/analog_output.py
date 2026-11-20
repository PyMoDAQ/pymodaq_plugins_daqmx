"""Set a voltage, then play a waveform clocked by the device."""
import numpy as np

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AOVoltage, AnalogOutputTask, ClockSettings, TaskConfig)


def main():
    channel = AOVoltage('Dev2/ao0', min_val=-5., max_val=5.)

    with AnalogOutputTask(TaskConfig(channels=[channel])) as task:
        task.write_levels([1.5])  # a DC level, applied at once

    waveform = np.sin(np.linspace(0, 2 * np.pi, 100))
    config = TaskConfig(channels=[channel], timing=ClockSettings(rate=1000., samples=len(waveform)))
    with AnalogOutputTask(config) as task:
        task.write_analog(waveform)  # written to the buffer, nothing is output yet
        task.start()  # 100 ms of sine
    return waveform


if __name__ == '__main__':
    main()
