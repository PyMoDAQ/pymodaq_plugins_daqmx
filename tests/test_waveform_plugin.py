"""Behaviour of the waveform output actuator (several analog outputs, one task), with the driver doubled."""
import types

import numpy as np
import pytest

pytest.importorskip('nidaqmx')
pytest.importorskip('pymodaq')
pytest.importorskip('pymodaq_plugins_utils')

from nidaqmx.constants import AcquisitionType, Edge
from pymodaq.utils.data import DataActuator
from pymodaq.utils.plugin_testing import make_actuator
from pymodaq_plugins_utils.hardware.waveform_output import WaveformOutput

from pymodaq_plugins_daqmx.daq_move_plugins.daq_move_NIDAQmx_Waveform import DAQ_Move_NIDAQmx_Waveform

from nidaqmx_double import driver, system_driver  # noqa: F401  (pytest fixtures)

CHANNELS = ['Dev2/ao0', 'Dev2/ao1']


def chosen(*names):
    return dict(all_items=['Dev2/ao0', 'Dev2/ao1', 'Dev2/ao2', 'Dev2/ao3'], selected=list(names))


@pytest.fixture
def plugin(qapp, driver, system_driver):
    plugin = make_actuator(DAQ_Move_NIDAQmx_Waveform, channels=chosen(*CHANNELS))
    yield plugin
    plugin.close()


def position(*rows):
    return DataActuator(data=[np.asarray(row, dtype=float) for row in rows], units='V')


def waveform_tasks(driver, kind='ao_voltage'):
    return [t for t in driver if t.channels and t.channels[0][0] == kind and t.timing_calls]


def set_output(plugin, **choices):
    for name, value in choices.items():
        plugin.settings.child('waveform_output', name).setValue(value)


def test_the_outputs_are_offered_and_held_at_zero_at_start(plugin, driver):
    assert 'Dev2/ao3' in plugin.settings['channels']['all_items']
    (task,) = [t for t in driver if t.channels]
    assert [c[1] for c in task.channels] == CHANNELS and task.writes == [([[0.], [0.]], True)]
    assert plugin.axis_unit == 'V'


def test_the_capabilities_follow_the_device_and_the_contract(plugin):
    waveform_output = WaveformOutput.from_module(_Module(plugin))
    assert waveform_output.n_channels == 2
    assert (waveform_output.min_rate, waveform_output.max_rate) == (pytest.approx(0.1), pytest.approx(2857142.857))
    assert (waveform_output.min_voltage, waveform_output.max_voltage) == (-10., 10.)
    assert [mode.value for mode in waveform_output.modes] == ['finite', 'repeat', 'continuous']
    assert '/Dev2/PFI0' in waveform_output.triggers and waveform_output.live_update is False
    assert waveform_output.max_samples == 1000000


class _Module:
    """What an application has: a control module whose settings hold the ones of the plugin"""
    _hw_settings_name = 'hw'

    def __init__(self, plugin):
        self.settings = types.SimpleNamespace(child=lambda name: plugin.settings)


def test_a_finite_waveform_is_one_task_with_one_clock_for_all_the_outputs(plugin, driver):
    set_output(plugin, sample_rate=1e4, mode='finite')
    plugin.move_abs(position(np.linspace(0, 1, 100), np.linspace(1, 0, 100)))

    (task,) = waveform_tasks(driver)
    assert [c[1] for c in task.channels] == CHANNELS
    (call,) = task.timing_calls
    assert call[1] == 1e4 and call[2]['sample_mode'] == AcquisitionType.FINITE and call[2]['samps_per_chan'] == 100
    data, auto_start = task.writes[-1]
    assert np.array(data).shape == (2, 100) and auto_start is False
    assert task.started and plugin.ispolling is False
    assert [len(row) for row in plugin.get_actuator_value().data] == [100, 100]


def test_a_repeated_waveform_is_the_samples_several_times(plugin, driver):
    set_output(plugin, sample_rate=1e4, mode='repeat', repetitions=3)
    plugin.move_abs(position([0., 1., 2.], [3., 4., 5.]))

    (task,) = waveform_tasks(driver)
    assert task.timing_calls[0][2]['samps_per_chan'] == 9
    assert np.array(task.writes[-1][0]).tolist() == [[0., 1., 2.] * 3, [3., 4., 5.] * 3]


def test_a_continuous_waveform_regenerates_a_buffer_of_its_size(plugin, driver):
    set_output(plugin, sample_rate=1e4, mode='continuous')
    plugin.move_abs(position(np.zeros(50), np.ones(50)))

    (task,) = waveform_tasks(driver)
    call = task.timing_calls[0]
    assert call[2]['sample_mode'] == AcquisitionType.CONTINUOUS and call[2]['samps_per_chan'] == 50


def test_what_the_instrument_cannot_do_is_refused_with_a_reason_and_nothing_is_played(plugin, driver):
    set_output(plugin, sample_rate=1e4)
    with pytest.raises(ValueError, match='2 channels'):
        plugin.move_abs(position(np.zeros(10)))
    with pytest.raises(ValueError, match='V to 20 V'):
        plugin.move_abs(position(np.full(10, 20.), np.zeros(10)))
    set_output(plugin, sample_rate=1e8)
    with pytest.raises(ValueError, match='Sample rate'):
        plugin.move_abs(position(np.zeros(10), np.zeros(10)))
    assert not waveform_tasks(driver)


def test_the_samples_are_cut_by_the_max_samples_setting_with_a_clear_error(plugin, driver):
    plugin.settings.child('max_samples').setValue(20)
    plugin.commit_settings(plugin.settings.child('max_samples'))  # what the Dashboard does when a setting is edited
    with pytest.raises(ValueError, match='at most 20'):
        plugin.move_abs(position(np.zeros(30), np.zeros(30)))


def test_a_start_trigger_and_an_external_clock_are_given_to_the_task(plugin, driver):
    plugin.settings.child('trigger').setValue('/Dev2/PFI0')
    plugin.settings.child('trigger_edge').setValue('falling')
    plugin.settings.child('clock_source').setValue('/Dev2/PFI1')
    plugin.move_abs(position(np.zeros(10), np.zeros(10)))

    (task,) = waveform_tasks(driver)
    assert task.trigger_calls == [('dig_edge', '/Dev2/PFI0', Edge.FALLING)]
    assert task.timing_calls[0][2]['source'] == '/Dev2/PFI1'


def test_a_new_waveform_replaces_the_previous_one(plugin, driver):
    plugin.move_abs(position(np.zeros(10), np.zeros(10)))
    plugin.move_abs(position(np.ones(20), np.ones(20)))

    first, second = waveform_tasks(driver)
    assert first.closed and not second.closed and second.timing_calls[0][2]['samps_per_chan'] == 20


def test_the_end_of_a_finite_waveform_is_announced(plugin, driver, qtbot):
    sent = []
    plugin.emit_status = lambda status: status.command != 'update_settings' and sent.append(status)
    plugin.move_abs(position(np.zeros(10), np.zeros(10)))
    (task,) = waveform_tasks(driver)

    task.fire_done(0)

    qtbot.waitUntil(lambda: any(s.command == 'generation_done' and s.attribute == 0 for s in sent), timeout=2000)


def test_a_continuous_waveform_has_no_end(plugin, driver, qtbot):
    sent = []
    plugin.emit_status = lambda status: status.command != 'update_settings' and sent.append(status)
    set_output(plugin, mode='continuous')
    plugin.move_abs(position(np.zeros(10), np.zeros(10)))
    (task,) = waveform_tasks(driver)

    task.fire_done(0)
    qtbot.wait(200)

    assert not [status for status in sent if status.command == 'generation_done']


def test_stop_and_close_bring_the_outputs_to_zero(plugin, driver):
    plugin.move_abs(position(np.ones(10), np.ones(10)))
    (played,) = waveform_tasks(driver)

    plugin.stop_motion()

    assert played.closed
    holder = [t for t in driver if t.channels and not t.timing_calls][-1]
    assert holder.writes[-1] == ([[0.], [0.]], True) and not holder.closed
    plugin.close()
    assert holder.closed


def test_a_choice_of_outputs_on_several_devices_or_none_is_refused(qapp, driver, system_driver):
    with pytest.raises(ValueError, match='no analog output'):
        make_actuator(DAQ_Move_NIDAQmx_Waveform, channels=chosen())
    with pytest.raises(ValueError, match='one device'):
        make_actuator(DAQ_Move_NIDAQmx_Waveform, channels=dict(all_items=['Dev2/ao0', 'Dev1/ao0'],
                                                               selected=['Dev2/ao0', 'Dev1/ao0']))
