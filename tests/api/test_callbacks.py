"""Public API: being told what the task does (no hardware nor NI-DAQmx driver needed)."""
import gc
import threading

import numpy as np
import pytest

pytest.importorskip('nidaqmx')

from nidaqmx_double import driver  # noqa: F401  (pytest fixture)

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AIVoltage, AnalogInputTask, ClockSettings, TaskConfig, TaskListener)


class Recorder(AnalogInputTask):
    def __init__(self, config):
        super().__init__(config)
        self.blocks = []
        self.done = []
        self.threads = []

    def on_samples_ready(self, data):
        self.blocks.append(data)
        self.threads.append(threading.current_thread().name)

    def on_done(self, status):
        self.done.append(status)


def make(driver):
    config = TaskConfig(channels=[AIVoltage('Dev1/ai0')], timing=ClockSettings(rate=1000., samples=4))
    return Recorder(config), driver[-1]


def test_on_samples_ready_receives_each_block_as_a_2d_array(driver):
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


def test_the_task_can_be_started_again_and_still_reports(driver):
    task, nidaqmx_task = make(driver)
    task.start(notify_every=2)
    task.stop()

    task.start(notify_every=2)  # the driver refuses to register an event twice

    nidaqmx_task.fire_samples()
    nidaqmx_task.fire_done(0)
    assert len(task.blocks) == 1 and task.done == [0]
    assert nidaqmx_task.starts == 2


def test_the_block_size_can_change_between_two_runs(driver):
    task, nidaqmx_task = make(driver)
    task.start(notify_every=2)
    task.stop()

    task.start(notify_every=3)

    nidaqmx_task.fire_samples()
    assert nidaqmx_task._every_n[0] == 3 and len(task.blocks) == 1


def test_a_run_without_blocks_after_a_run_with_blocks_stops_the_notifications(driver):
    task, nidaqmx_task = make(driver)
    task.start(notify_every=2)
    task.stop()

    task.start()

    assert nidaqmx_task._every_n is None


class Listener(TaskListener):
    def __init__(self):
        self.blocks, self.done, self.threads = [], [], []

    def on_samples_ready(self, data):
        self.blocks.append(data)
        self.threads.append(threading.current_thread().name)

    def on_done(self, status):
        self.done.append(status)


def make_plain(driver):
    config = TaskConfig(channels=[AIVoltage('Dev1/ai0')], timing=ClockSettings(rate=1000., samples=4))
    return AnalogInputTask(config), driver[-1]


def test_a_listener_is_told_about_the_blocks_and_the_end_of_the_task(driver):
    task, nidaqmx_task = make_plain(driver)
    listener = Listener()
    task.add_listener(listener)

    task.start(notify_every=2)
    nidaqmx_task.fire_samples()
    nidaqmx_task.fire_done(0)

    assert len(listener.blocks) == 1 and listener.blocks[0].shape == (1, 2)
    assert listener.done == [0]
    assert listener.threads == ['driver']


def test_several_listeners_are_all_told_and_a_removed_one_is_not(driver):
    task, nidaqmx_task = make_plain(driver)
    first, second = Listener(), Listener()
    task.add_listener(first)
    task.add_listener(second)
    task.remove_listener(first)

    task.start()
    nidaqmx_task.fire_done(0)

    assert first.done == [] and second.done == [0]


def test_a_closed_task_does_not_keep_its_listeners(driver):
    import gc
    import weakref
    task, _ = make_plain(driver)
    listener = Listener()
    reference = weakref.ref(listener)
    task.add_listener(listener)

    task.close()
    del listener
    gc.collect()

    assert reference() is None  # the closed task does not hold the listener any longer
