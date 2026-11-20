"""Acquire 100 samples and be told as each block of 10 is ready."""

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AIVoltage, AnalogInputTask, ClockSettings, TaskConfig, TaskListener)


class Recorder(TaskListener):
    """What a task tells: the driver calls these from threads of its own, not from yours."""

    def __init__(self):
        self.blocks = []
        self.status = None

    def on_samples_ready(self, data):  # data is shaped (channels, samples); keep it short, hand it over
        self.blocks.append(data)

    def on_done(self, status):  # 0 when the task ended normally
        self.status = status


def main():
    config = TaskConfig(channels=[AIVoltage('Dev1/ai0')], timing=ClockSettings(rate=1000., samples=100))
    recorder = Recorder()
    with AnalogInputTask(config) as task:
        task.add_listener(recorder)
        task.start(notify_every=10)  # one block of 10 samples at a time
        # ... wait, for example with a threading.Event set from on_done, then use recorder.blocks
    return recorder
