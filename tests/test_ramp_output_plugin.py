"""Behaviour of the ramp output actuator against a fake of the NIDAQmx wrapper (no hardware, no NI driver)."""
import pytest

pytest.importorskip('nidaqmx')
pytest.importorskip('pymodaq')

from pymodaq.utils.plugin_testing import make_actuator

from pymodaq_plugins_daqmx.hardware.national_instruments import ramp_output
from pymodaq_plugins_daqmx.daq_move_plugins import daq_move_NIDAQmx_RampOutput as module
from pymodaq_plugins_daqmx.daq_move_plugins.daq_move_NIDAQmx_RampOutput import DAQ_Move_NIDAQmx_RampOutput

from fake_nidaqmx import FakeNIDAQmx


class Clock:
    """A clock of the tests, advanced by hand"""
    def __init__(self):
        self.now = 0.

    def __call__(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    monkeypatch.setattr(ramp_output, 'NIDAQmx', FakeNIDAQmx)
    return Clock()


@pytest.fixture
def actuator(qapp, clock):
    plugin = make_actuator(DAQ_Move_NIDAQmx_RampOutput, analog_channel='Dev1/ao0', clock_channel='Dev1/ctr0',
                           step_size=100., step_time=10., conv_factor=1000.)
    plugin.controller._time = clock
    assert plugin.initialized
    yield plugin
    plugin.close()


def test_init_puts_the_output_to_zero(actuator):
    assert actuator.controller.analog.writes[0] == (0., True)
    assert actuator.get_actuator_value().value('nm') == 0.


def test_a_short_move_is_a_single_write(actuator):
    actuator.move_abs(actuator.get_actuator_value().__class__(data=50., units='nm'))
    assert actuator.controller.analog.writes[-1] == (0.05, True)
    assert actuator.get_actuator_value().value('nm') == pytest.approx(50.)


def test_a_long_move_is_a_timed_ramp(actuator, clock):
    from pymodaq.utils.data import DataActuator
    actuator.move_abs(DataActuator(data=500., units='nm'))
    analog, ctrl_clock = actuator.controller.analog, actuator.controller.clock
    data, auto_start = analog.writes[-1]
    assert data == pytest.approx([0.1, 0.2, 0.3, 0.4, 0.5]) and not auto_start
    name, rate, kwargs = analog.task.timing.calls[0]
    assert rate == pytest.approx(100.) and kwargs['source'] == '/Dev1/ctr0InternalOutput'
    assert kwargs['samps_per_chan'] == 5
    assert ctrl_clock.task.timing.calls[0][1]['samps_per_chan'] == 6
    assert analog.task.running and ctrl_clock.task.running


def test_position_follows_the_ramp_in_time(actuator, clock):
    from pymodaq.utils.data import DataActuator
    actuator.move_abs(DataActuator(data=500., units='nm'))
    clock.now = 0.025  # third step
    assert actuator.get_actuator_value().value('nm') == pytest.approx(300.)
    assert actuator.controller.is_moving()
    clock.now = 1.
    assert actuator.get_actuator_value().value('nm') == pytest.approx(500.)
    assert not actuator.controller.is_moving()


def test_stop_keeps_the_reached_position(actuator, clock):
    from pymodaq.utils.data import DataActuator
    actuator.move_abs(DataActuator(data=500., units='nm'))
    clock.now = 0.015
    actuator.stop_motion()
    clock.now = 1.
    assert actuator.get_actuator_value().value('nm') == pytest.approx(200.)


def test_relative_move_from_the_position_reached(actuator, clock):
    from pymodaq.utils.data import DataActuator
    actuator.move_abs(DataActuator(data=300., units='nm'))
    clock.now = 1.
    actuator.current_value = actuator.get_actuator_value()
    actuator.move_rel(DataActuator(data=-300., units='nm'))
    assert actuator.controller.analog.writes[-1][0] == pytest.approx([0.2, 0.1, 0.])


def test_other_axes_stay_where_they_are(qapp, clock):
    ctrl = ramp_output.RampOutputController()
    ctrl._time = clock
    ctrl.clock_channel = 'Dev1/ctr0'
    ctrl.configure_axis('x', 'Dev1/ao0', -10., 10.)
    ctrl.configure_axis('y', 'Dev1/ao1', -10., 10.)
    ctrl.ramp('x', [1.], 0.01)
    ctrl.ramp('y', [0.1, 0.2], 0.01)
    data, _ = ctrl.analog.writes[-1]
    assert data == [[1., 1.], [0.1, 0.2]]


def test_an_axis_moved_during_the_ramp_of_another_one_does_not_stop_it(qapp, clock):
    ctrl = ramp_output.RampOutputController()
    ctrl._time = clock
    ctrl.clock_channel = 'Dev1/ctr0'
    ctrl.configure_axis('x', 'Dev1/ao0', -10., 10.)
    ctrl.configure_axis('y', 'Dev1/ao1', -10., 10.)
    ctrl.ramp('x', [0.1, 0.2, 0.3, 0.4, 0.5], 0.01)
    clock.now = 0.015  # x is at its second step
    ctrl.ramp('y', [1., 2.], 0.01)
    x, y = ctrl.analog.writes[-1][0]
    assert x == pytest.approx([0.2, 0.3, 0.4, 0.5])  # x carries on to its target
    assert y == pytest.approx([1., 2., 2., 2.])  # y reaches its own, then stays
    clock.now = 1.
    assert ctrl.voltage('x') == pytest.approx(0.5) and ctrl.voltage('y') == pytest.approx(2.)
