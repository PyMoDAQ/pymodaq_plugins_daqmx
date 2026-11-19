"""Public API: acquiring analog voltages (no hardware nor NI-DAQmx driver needed)."""
import numpy as np
import pytest

pytest.importorskip('nidaqmx')

from nidaqmx_double import driver  # noqa: F401  (pytest fixture)

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AIVoltage, AnalogInputTask, ClockSettings, TaskConfig)


def test_reads_one_voltage_channel_as_a_2d_float_array(driver):
    config = TaskConfig(channels=[AIVoltage('Dev1/ai0', min_val=-5., max_val=5.)],
                        timing=ClockSettings(rate=1000., samples=4))

    with AnalogInputTask(config) as task:
        data = task.read_analog()

    assert data.dtype == np.float64
    assert data.shape == (1, 4)
    np.testing.assert_allclose(data, [[0.0, 0.1, 0.2, 0.3]])


def test_reads_two_channels_one_row_per_channel(driver):
    config = TaskConfig(channels=[AIVoltage('Dev1/ai0'), AIVoltage('Dev1/ai1')],
                        timing=ClockSettings(rate=1000., samples=3))

    with AnalogInputTask(config) as task:
        data = task.read_analog()

    np.testing.assert_allclose(data, [[0.0, 0.1, 0.2], [1.0, 1.1, 1.2]])


def test_reads_a_single_sample_from_each_channel_as_a_column(driver):
    config = TaskConfig(channels=[AIVoltage('Dev1/ai0'), AIVoltage('Dev1/ai1')],
                        timing=ClockSettings(rate=1000., samples=1))

    with AnalogInputTask(config) as task:
        data = task.read_analog()

    assert data.shape == (2, 1)


def test_an_inverted_range_is_refused_before_touching_the_driver(driver):
    with pytest.raises(ValueError, match='min_val'):
        AIVoltage('Dev1/ai0', min_val=5., max_val=-5.)

    assert driver == []


def test_a_driver_error_reaches_the_caller_and_the_task_is_released(driver):
    import nidaqmx
    config = TaskConfig(channels=[AIVoltage('Dev1/ai0'), AIVoltage('Dev1/ai9999')],
                        timing=ClockSettings(rate=1000., samples=3))

    with pytest.raises(nidaqmx.DaqError) as error:
        AnalogInputTask(config)

    assert error.value.error_code == -200170
    assert [task.closed for task in driver] == [True]

