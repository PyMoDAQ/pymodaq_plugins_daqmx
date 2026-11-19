"""Public API: reading and driving digital lines (no hardware nor NI-DAQmx driver needed)."""
import numpy as np
import pytest

pytest.importorskip('nidaqmx')

from nidaqmx_double import driver  # noqa: F401  (pytest fixture)

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    DigitalIn, DigitalOut, DigitalTask, TaskConfig)


def test_lines_are_read_as_a_2d_boolean_array(driver):
    config = TaskConfig(channels=[DigitalIn('Dev2/port0/line0'), DigitalIn('Dev2/port0/line1')])

    with DigitalTask(config) as task:
        levels = task.read_digital()

    assert levels.dtype == np.bool_
    assert levels.tolist() == [[True], [False]]


def test_each_line_is_its_own_channel(driver):
    from nidaqmx.constants import LineGrouping
    DigitalTask(TaskConfig(channels=[DigitalIn('Dev2/port0/line0')]))

    ((kind, name, settings),) = driver[-1].channels

    assert (kind, name) == ('di', 'Dev2/port0/line0')
    assert settings['line_grouping'] == LineGrouping.CHAN_PER_LINE


def test_a_line_is_driven_high_and_the_level_is_applied_at_once(driver):
    with DigitalTask(TaskConfig(channels=[DigitalOut('Dev2/port0/line3')])) as task:
        task.write_digital(True)

    assert driver[-1].channels[0][0] == 'do'
    assert driver[-1].writes == [(True, True)]


@pytest.mark.parametrize('name', ['Dev2/port0/line0:3', 'Dev2/port0/line0,Dev2/port0/line1'])
def test_a_channel_is_one_line_not_a_range(name):
    with pytest.raises(ValueError, match='one line'):
        DigitalIn(name)


def test_inputs_and_outputs_cannot_share_a_task():
    with pytest.raises(ValueError, match='inputs and outputs'):
        DigitalTask(TaskConfig(channels=[DigitalIn('Dev2/port0/line0'), DigitalOut('Dev2/port0/line1')]))
