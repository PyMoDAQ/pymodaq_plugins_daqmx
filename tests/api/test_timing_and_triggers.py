"""Public API: clocking and triggering a task (no hardware nor NI-DAQmx driver needed)."""
import pytest

pytest.importorskip('nidaqmx')

from nidaqmx.constants import AcquisitionType, Edge

from nidaqmx_double import driver  # noqa: F401  (pytest fixture)

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AIVoltage, AnalogInputTask, ClockSettings, DigitalEdgeTrigger, TaskConfig)


def open_task(driver, **config):
    task = AnalogInputTask(TaskConfig(channels=[AIVoltage('Dev1/ai0')], **config))
    return task, driver[-1]


def test_the_sample_clock_can_come_from_another_device(driver):
    timing = ClockSettings(rate=500., samples=10, source='/Dev1/PFI1', edge=Edge.FALLING)

    task, nidaqmx_task = open_task(driver, timing=timing)

    (call,) = nidaqmx_task.timing_calls
    assert call[0] == 'samp_clk'
    assert call[1] == 500.
    assert call[2]['source'] == '/Dev1/PFI1'
    assert call[2]['active_edge'] == Edge.FALLING
    assert call[2]['sample_mode'] == AcquisitionType.FINITE
    assert call[2]['samps_per_chan'] == 10


@pytest.mark.parametrize('kwargs', [dict(rate=0., samples=10), dict(rate=-1., samples=10),
                                    dict(rate=100., samples=0)])
def test_a_clock_that_cannot_run_is_refused(kwargs):
    with pytest.raises(ValueError):
        ClockSettings(**kwargs)


def test_a_digital_edge_start_trigger_waits_for_a_pfi_line(driver):
    trigger = DigitalEdgeTrigger(source='/Dev1/PFI0', edge=Edge.RISING)

    task, nidaqmx_task = open_task(driver, timing=ClockSettings(rate=1000., samples=4), trigger=trigger)

    assert nidaqmx_task.trigger_calls == [('dig_edge', '/Dev1/PFI0', Edge.RISING)]


def test_without_a_trigger_the_task_starts_immediately(driver):
    task, nidaqmx_task = open_task(driver, timing=ClockSettings(rate=1000., samples=4))

    assert nidaqmx_task.trigger_calls == []
