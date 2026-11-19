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


def test_the_pulses_of_a_counter_output_are_a_terminal_usable_as_a_clock_source():
    from pymodaq_plugins_daqmx.hardware.national_instruments.api import counter_output_terminal

    # spelled like the terminal that the driver accepted on a PCIe-6363 (contract_report_Dev2.json)
    assert counter_output_terminal('Dev2/ctr1') == '/Dev2/Ctr1InternalOutput'
    assert counter_output_terminal('cDAQ1Mod1/ctr0') == '/cDAQ1Mod1/Ctr0InternalOutput'


def test_only_a_counter_has_a_terminal_of_pulses():
    from pymodaq_plugins_daqmx.hardware.national_instruments.api import counter_output_terminal

    with pytest.raises(ValueError, match='counter'):
        counter_output_terminal('Dev2/ao0')


def test_without_a_number_of_samples_the_acquisition_is_continuous(driver):
    task, nidaqmx_task = open_task(driver, timing=ClockSettings(rate=2000.))

    (call,) = nidaqmx_task.timing_calls
    assert call[2]['sample_mode'] == AcquisitionType.CONTINUOUS
    assert call[2]['samps_per_chan'] >= 2000  # the driver buffer holds at least one second


def test_a_continuous_acquisition_cannot_be_read_in_one_go(driver):
    task, _ = open_task(driver, timing=ClockSettings(rate=2000.))

    with pytest.raises(ValueError, match='continuous'):
        task.read_analog()
