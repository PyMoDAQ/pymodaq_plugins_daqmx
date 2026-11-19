"""Public API: being told what the task does (no hardware nor NI-DAQmx driver needed)."""
import gc
import threading

import numpy as np
import pytest

pytest.importorskip('nidaqmx')

from nidaqmx_double import driver  # noqa: F401  (pytest fixture)

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AIVoltage, AnalogInputTask, ClockSettings, TaskConfig)


class Recorder(AnalogInputTask):
    def __init__(self, config):
        super().__init__(config)
        self.blocks = []
        self.done = []
        self.threads = []

    def on_samples(self, data):
        self.blocks.append(data)
        self.threads.append(threading.current_thread().name)

    def on_done(self, status):
        self.done.append(status)


def make(driver):
    config = TaskConfig(channels=[AIVoltage('Dev1/ai0')], timing=ClockSettings(rate=1000., samples=4))
    return Recorder(config), driver[-1]


def test_on_samples_receives_each_block_as_a_2d_array(driver):
    task, nidaqmx_task = make(driver)

    task.start(notify_every=2)
    nidaqmx_task.fire_samples()

    assert nidaqmx_task.started
    assert len(task.blocks) == 1
    np.testing.assert_allclose(task.blocks[0], [[0.0, 0.1]])


def test_on_done_receives_the_status(driver):
    task, nidaqmx_task = make(driver)

    task.start()
    nidaqmx_task.fire_done(0)

    assert task.done == [0]


def test_callbacks_come_from_the_driver_thread_not_the_callers(driver):
    task, nidaqmx_task = make(driver)

    task.start(notify_every=2)
    nidaqmx_task.fire_samples()

    assert task.threads == ['driver']


def test_the_task_keeps_the_registered_callbacks_alive(driver):
    task, nidaqmx_task = make(driver)
    task.start(notify_every=2)

    gc.collect()
    nidaqmx_task.fire_samples()
    nidaqmx_task.fire_done(0)

    assert len(task.blocks) == 1 and task.done == [0]
