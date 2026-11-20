"""Public API: tasks that run together, started in a given order (no hardware nor NI-DAQmx driver needed)."""
import nidaqmx
import pytest

pytest.importorskip('nidaqmx')

from nidaqmx_double import DoubleTask, driver  # noqa: F401  (pytest fixture)

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AOVoltage, AnalogOutputTask, COPulseFreq, CounterOutputTask, ImplicitTiming, TaskConfig, TaskGroup)


def make_tasks():
    analog = AnalogOutputTask(TaskConfig(channels=[AOVoltage('Dev2/ao0')]))
    clock = CounterOutputTask(TaskConfig(channels=[COPulseFreq('Dev2/ctr1', frequency=100.)],
                                         timing=ImplicitTiming()))
    return analog, clock


def test_the_tasks_start_in_the_given_order_and_stop_in_the_reverse_order(driver):
    analog, clock = make_tasks()
    group = TaskGroup(analog, clock)  # the analog output waits for the clock: it is armed first

    group.start()
    group.stop()

    assert DoubleTask.log == [('start', 'Dev2/ao0'), ('start', 'Dev2/ctr1'),
                              ('stop', 'Dev2/ctr1'), ('stop', 'Dev2/ao0')]


def test_close_closes_the_tasks_in_the_reverse_order(driver):
    group = TaskGroup(*make_tasks())

    group.close()

    assert DoubleTask.log == [('close', 'Dev2/ctr1'), ('close', 'Dev2/ao0')]


def test_a_task_that_cannot_start_leaves_the_others_stopped(driver):
    analog, clock = make_tasks()
    driver[1].start = lambda: (_ for _ in ()).throw(nidaqmx.DaqError('resource reserved', -50103))
    group = TaskGroup(analog, clock)

    with pytest.raises(nidaqmx.DaqError) as error:
        group.start()

    assert error.value.error_code == -50103
    assert DoubleTask.log == [('start', 'Dev2/ao0'), ('stop', 'Dev2/ao0')]


def test_every_task_is_closed_even_if_one_cannot_be(driver):
    analog, clock = make_tasks()
    driver[1].close = lambda: (_ for _ in ()).throw(nidaqmx.DaqError('already closed', -200088))
    group = TaskGroup(analog, clock)

    with pytest.raises(nidaqmx.DaqError):
        group.close()

    assert driver[0].closed


def test_the_group_is_a_context_manager_that_closes_the_tasks(driver):
    with TaskGroup(*make_tasks()) as group:
        group.start()

    assert all(task.closed for task in driver)
