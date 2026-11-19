"""Behaviour of the ramp output actuator, with the NI-DAQmx driver replaced by a double (no hardware needed)."""
import pytest

pytest.importorskip('nidaqmx')
pytest.importorskip('pymodaq')

from nidaqmx.constants import AcquisitionType
from pymodaq.control_modules.thread_commands import ControllerStatus
from pymodaq.utils.data import DataActuator
from pymodaq.utils.plugin_testing import make_actuator

from pymodaq_plugins_daqmx.daq_move_plugins.daq_move_NIDAQmx_RampOutput import DAQ_Move_NIDAQmx_RampOutput

from nidaqmx_double import driver  # noqa: F401  (pytest fixture)


class Clock:
    """A clock of the tests, advanced by hand"""
    def __init__(self):
        self.now = 0.

    def __call__(self):
        return self.now


def analog_tasks(driver):
    return [t for t in driver if t.channels and t.channels[0][0] == 'ao_voltage']


def clock_tasks(driver):
    return [t for t in driver if t.channels and t.channels[0][0] == 'co_pulse_freq']


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def actuator(qapp, driver, clock):
    plugin = make_actuator(DAQ_Move_NIDAQmx_RampOutput, analog_channel='Dev2/ao0', clock_channel='Dev2/ctr0',
                           step_size=100., step_time=10., conv_factor=1000.)
    plugin.controller._time = clock
    assert plugin.initialized
    yield plugin
    plugin.close()


def make_slave(master, channel, axis):
    """A second axis (y, z) sharing the controller, hence the clock, of the master."""
    plugin = DAQ_Move_NIDAQmx_RampOutput()
    plugin.settings.child('controller', 'controller_status').setValue(ControllerStatus.SLAVE)
    plugin.settings.child('controller', 'axis').setValue(axis)
    plugin.settings.child('analog_channel').setValue(channel)
    plugin.settings.child('step_size').setValue(1000.)
    plugin.settings.child('step_time').setValue(10.)
    plugin.settings.child('conv_factor').setValue(1000.)
    plugin.ini_stage(master.controller)
    return plugin


def test_init_puts_the_output_to_zero(actuator, driver):
    assert analog_tasks(driver)[0].writes[0] == (0., True)
    assert actuator.get_actuator_value().value('nm') == 0.


def test_a_short_move_is_a_single_write(actuator, driver):
    actuator.move_abs(DataActuator(data=50., units='nm'))
    assert analog_tasks(driver)[-1].writes[-1] == (0.05, True)
    assert actuator.get_actuator_value().value('nm') == pytest.approx(50.)


def test_a_long_move_is_a_timed_ramp(actuator, driver, clock):
    actuator.move_abs(DataActuator(data=500., units='nm'))
    analog, pulses = analog_tasks(driver)[-1], clock_tasks(driver)[-1]
    data, auto_start = analog.writes[-1]
    assert data == pytest.approx([0.1, 0.2, 0.3, 0.4, 0.5]) and not auto_start
    name, rate, kwargs = analog.timing_calls[0]
    assert rate == pytest.approx(100.) and kwargs['source'] == '/Dev2/Ctr0InternalOutput'
    assert kwargs['samps_per_chan'] == 5
    assert pulses.timing_calls[0] == ('implicit', AcquisitionType.FINITE, 6)
    assert analog.started and pulses.started


def test_position_follows_the_ramp_in_time(actuator, clock):
    actuator.move_abs(DataActuator(data=500., units='nm'))
    clock.now = 0.025  # third step
    assert actuator.get_actuator_value().value('nm') == pytest.approx(300.)
    assert actuator.controller.is_moving()
    clock.now = 1.
    assert actuator.get_actuator_value().value('nm') == pytest.approx(500.)
    assert not actuator.controller.is_moving()


def test_stop_keeps_the_reached_position(actuator, clock, driver):
    actuator.move_abs(DataActuator(data=500., units='nm'))
    clock.now = 0.015
    actuator.stop_motion()
    clock.now = 1.
    assert actuator.get_actuator_value().value('nm') == pytest.approx(200.)
    assert not analog_tasks(driver)[-1].started and not clock_tasks(driver)[-1].started


def test_relative_move_from_the_position_reached(actuator, clock, driver):
    actuator.move_abs(DataActuator(data=300., units='nm'))
    clock.now = 1.
    actuator.current_value = actuator.get_actuator_value()
    actuator.move_rel(DataActuator(data=-300., units='nm'))
    assert analog_tasks(driver)[-1].writes[-1][0] == pytest.approx([0.2, 0.1, 0.])


def test_other_axes_stay_where_they_are(actuator, driver, clock):
    y = make_slave(actuator, 'Dev2/ao1', 'y')
    actuator.move_abs(DataActuator(data=100., units='nm'))  # one step
    y.move_abs(DataActuator(data=2000., units='nm'))  # two steps
    data, _ = analog_tasks(driver)[-1].writes[-1]
    assert data == [[0.1, 0.1], [1., 2.]]


def test_an_axis_moved_during_the_ramp_of_another_one_does_not_stop_it(actuator, driver, clock):
    y = make_slave(actuator, 'Dev2/ao1', 'y')
    actuator.move_abs(DataActuator(data=500., units='nm'))
    clock.now = 0.015  # x is at its second step
    y.move_abs(DataActuator(data=2000., units='nm'))
    x_values, y_values = analog_tasks(driver)[-1].writes[-1][0]
    assert x_values == pytest.approx([0.2, 0.3, 0.4, 0.5])  # x carries on to its target
    assert y_values[-1] == pytest.approx(2.) and len(y_values) == 4  # y reaches its own, then stays
    clock.now = 1.
    assert actuator.controller.voltage('x') == pytest.approx(0.5)
    assert actuator.controller.voltage('y') == pytest.approx(2.)


def test_close_releases_the_tasks(actuator, driver):
    actuator.move_abs(DataActuator(data=500., units='nm'))
    actuator.close()
    assert all(t.closed for t in analog_tasks(driver) + clock_tasks(driver))
