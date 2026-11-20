"""Acquire a block of voltages on two channels and read it as a (channels, samples) array."""
from nidaqmx.constants import TerminalConfiguration

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AIVoltage, AnalogInputTask, ClockSettings, TaskConfig)


def main():
    config = TaskConfig(
        channels=[AIVoltage('Dev1/ai0', min_val=-5., max_val=5., terminal_config=TerminalConfiguration.DIFF),
                  AIVoltage('Dev1/ai1', min_val=-5., max_val=5., terminal_config=TerminalConfiguration.DIFF)],
        timing=ClockSettings(rate=10_000., samples=1000))  # 1000 samples per channel, 0.1 s

    with AnalogInputTask(config) as task:  # the task is released when the block is left, whatever happens
        task.start()
        data = task.read_analog()  # float64, shaped (2, 1000); waits for the end of the acquisition
        task.stop()
    return data


if __name__ == '__main__':
    print(main().mean(axis=1))
