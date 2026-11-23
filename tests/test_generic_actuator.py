"""Behaviour of the generic NI output actuator (one analog output or digital line), with the driver doubled."""
import pytest

pytest.importorskip('nidaqmx')
pytest.importorskip('pymodaq')

from pymodaq.utils.data import DataActuator
from pymodaq.utils.plugin_testing import make_actuator

from pymodaq_plugins_daqmx.daq_move_plugins.daq_move_NIDAQmx import DAQ_Move_NIDAQmx
from pymodaq_plugins_daqmx.daq_move_plugins.daq_move_NIDAQmx_DO import DAQ_Move_NIDAQmx_DO

from nidaqmx_double import driver, system_driver  # noqa: F401  (pytest fixtures)


def output_tasks(driver):
    return [t for t in driver if t.channels and t.channels[0][0] in ('ao_voltage', 'ao_current', 'do')]


def test_the_analog_actuator_offers_the_analog_outputs_and_the_digital_one_the_lines(qapp, driver, system_driver):
    analog = make_actuator(DAQ_Move_NIDAQmx, channel='Dev2/ao0')
    digital = make_actuator(DAQ_Move_NIDAQmx_DO, channel='Dev2/port0/line0')
    assert 'Dev2/ao0' in analog.settings.child('channel').opts['limits']
    assert not [c for c in analog.settings.child('channel').opts['limits'] if '/port' in c]
    assert 'Dev2/port0/line0' in digital.settings.child('channel').opts['limits']
    assert not [c for c in digital.settings.child('channel').opts['limits'] if '/ao' in c]
    analog.close()
    digital.close()


def test_an_analog_output_is_set_to_zero_at_start_and_moves_to_a_level(qapp, driver, system_driver):
    plugin = make_actuator(DAQ_Move_NIDAQmx, channel='Dev2/ao0')
    task = output_tasks(driver)[0]
    assert task.channels[0][0] == 'ao_voltage' and task.writes == [(0., True)]
    assert plugin.axis_unit == 'V' and plugin.get_actuator_value().value('V') == 0.
    plugin.move_abs(DataActuator(data=2.5, units='V'))
    assert task.writes[-1] == (2.5, True) and plugin.get_actuator_value().value('V') == pytest.approx(2.5)
    plugin.move_rel(DataActuator(data=-1., units='V'))
    assert task.writes[-1] == (1.5, True)
    plugin.close()


def test_a_level_outside_the_range_of_the_output_is_cut_to_it(qapp, driver, system_driver):
    plugin = make_actuator(DAQ_Move_NIDAQmx, channel='Dev2/ao0', min_val=-2., max_val=3.)
    plugin.move_abs(DataActuator(data=7., units='V'))
    assert output_tasks(driver)[0].writes[-1] == (3., True)
    plugin.close()


def test_a_current_output_is_in_amperes(qapp, driver, system_driver):
    plugin = make_actuator(DAQ_Move_NIDAQmx, channel='Dev2/ao1', type='current', min_val=0., max_val=0.02)
    assert output_tasks(driver)[0].channels[0][0] == 'ao_current' and plugin.axis_unit == 'A'
    plugin.close()


def test_the_output_goes_back_to_zero_when_the_plugin_closes(qapp, driver, system_driver):
    plugin = make_actuator(DAQ_Move_NIDAQmx, channel='Dev2/ao0')
    plugin.move_abs(DataActuator(data=4., units='V'))
    task = output_tasks(driver)[0]
    plugin.close()
    assert task.writes[-1] == (0., True) and task.closed


def test_changing_the_channel_zeroes_the_old_output_and_drives_the_new_one(qapp, driver, system_driver):
    plugin = make_actuator(DAQ_Move_NIDAQmx, channel='Dev2/ao0')
    plugin.move_abs(DataActuator(data=4., units='V'))
    plugin.settings.child('channel').setValue('Dev2/ao1')
    plugin.commit_settings(plugin.settings.child('channel'))
    old, new = output_tasks(driver)[:2]
    assert old.writes[-1] == (0., True) and old.closed
    assert new.channels[0][1] == 'Dev2/ao1' and new.writes == [(0., True)]
    plugin.close()


def test_a_digital_line_is_driven_to_a_level_and_has_no_unit(qapp, driver, system_driver):
    plugin = make_actuator(DAQ_Move_NIDAQmx_DO, channel='Dev2/port0/line1')
    task = output_tasks(driver)[0]
    assert task.channels[0][0] == 'do' and task.writes == [(False, True)]
    assert plugin.axis_unit == ''
    plugin.move_abs(DataActuator(data=1., units=''))
    assert task.writes[-1] == (True, True) and plugin.get_actuator_value().value() == 1.
    plugin.close()
    assert task.writes[-1] == (False, True) and task.closed


def test_a_pulse_sets_the_line_high_for_a_while_then_low_again(qapp, driver, system_driver):
    plugin = make_actuator(DAQ_Move_NIDAQmx_DO, channel='Dev2/port0/line1', pulse=True, pulse_width=1.)
    task = output_tasks(driver)[0]
    plugin.move_abs(DataActuator(data=1., units=''))
    assert [w[0] for w in task.writes] == [False, True, False]
    assert plugin.get_actuator_value().value() == 0.  # the line is low again
    plugin.close()


def test_each_pulse_is_logged_and_counted(qapp, driver, system_driver):
    plugin = make_actuator(DAQ_Move_NIDAQmx_DO, channel='Dev2/port0/line1', pulse=True, pulse_width=1.)
    sent = []
    plugin.emit_status = lambda status: status.command != 'update_settings' and sent.append(status)
    assert plugin.settings['pulses'] == 0 and plugin.settings.child('pulses').opts['readonly']
    plugin.move_abs(DataActuator(data=1., units=''))
    plugin.move_abs(DataActuator(data=1., units=''))
    assert plugin.settings['pulses'] == 2
    assert [s.command for s in sent] == ['Update_Status', 'Update_Status']
    assert 'Dev2/port0/line1' in sent[0].attribute[0] and '1' in sent[0].attribute[0]
    plugin.move_abs(DataActuator(data=0., units=''))  # a move to 0 is no pulse
    assert plugin.settings['pulses'] == 2
    plugin.close()


def test_each_actuator_asks_for_its_user_interface():
    from pymodaq.control_modules.daq_move_ui.utils import UiType
    assert DAQ_Move_NIDAQmx.ui_type == UiType.SIMPLE
    assert DAQ_Move_NIDAQmx_DO.ui_type == UiType.BINARY
