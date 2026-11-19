"""Public API: driving analog outputs (no hardware nor NI-DAQmx driver needed)."""
import pytest

pytest.importorskip('nidaqmx')

from nidaqmx_double import driver  # noqa: F401  (pytest fixture)

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AnalogOutputTask, AOVoltage, ClockSettings, TaskConfig)


def test_a_dc_level_is_written_and_starts_immediately(driver):
    with AnalogOutputTask(TaskConfig(channels=[AOVoltage('Dev2/ao0')])) as task:
        task.write_analog(1.5)

    assert driver[-1].writes == [(1.5, True)]


def test_a_waveform_is_written_before_the_task_is_started(driver):
    config = TaskConfig(channels=[AOVoltage('Dev2/ao0')], timing=ClockSettings(rate=1000., samples=4))

    with AnalogOutputTask(config) as task:
        task.write_analog([0.0, 0.1, 0.2, 0.3])

    assert driver[-1].writes == [([0.0, 0.1, 0.2, 0.3], False)]


def test_two_channels_take_one_row_each(driver):
    config = TaskConfig(channels=[AOVoltage('Dev2/ao0'), AOVoltage('Dev2/ao1')],
                        timing=ClockSettings(rate=1000., samples=2))

    with AnalogOutputTask(config) as task:
        task.write_analog([[0.0, 0.1], [1.0, 1.1]])

    assert driver[-1].writes == [([[0.0, 0.1], [1.0, 1.1]], False)]


def test_data_for_the_wrong_number_of_channels_is_refused_before_the_driver(driver):
    config = TaskConfig(channels=[AOVoltage('Dev2/ao0'), AOVoltage('Dev2/ao1')],
                        timing=ClockSettings(rate=1000., samples=3))

    with AnalogOutputTask(config) as task:
        with pytest.raises(ValueError, match='2 channels'):
            task.write_analog([0.0, 0.1, 0.2])

    assert driver[-1].writes == []


def test_levels_set_every_output_at_once_and_start_immediately(driver):
    config = TaskConfig(channels=[AOVoltage('Dev2/ao0'), AOVoltage('Dev2/ao1')])

    with AnalogOutputTask(config) as task:
        task.write_levels([0.5, -0.5])

    assert driver[-1].writes == [([[0.5], [-0.5]], True)]


def test_one_level_for_a_single_output(driver):
    with AnalogOutputTask(TaskConfig(channels=[AOVoltage('Dev2/ao0')])) as task:
        task.write_levels([2.0])

    assert driver[-1].writes == [(2.0, True)]


def test_levels_for_the_wrong_number_of_outputs_are_refused_before_the_driver(driver):
    config = TaskConfig(channels=[AOVoltage('Dev2/ao0'), AOVoltage('Dev2/ao1')])

    with AnalogOutputTask(config) as task:
        with pytest.raises(ValueError, match='2 channels'):
            task.write_levels([0.5])

    assert driver[-1].writes == []
