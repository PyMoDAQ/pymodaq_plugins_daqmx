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
