"""Behaviour of the generic NI viewer: its channels come from the settings tree (no hardware needed)."""
import pytest

pytest.importorskip('nidaqmx')
pytest.importorskip('pymodaq')

from pymodaq.utils.plugin_testing import make_detector, grab_and_wait

from pymodaq_plugins_daqmx.daq_viewer_plugins.plugins_0D.daq_0Dviewer_NIDAQmx import DAQ_0DViewer_NIDAQmx

from nidaqmx_double import driver, system_driver  # noqa: F401  (pytest fixtures)


def test_the_channels_added_to_the_tree_are_acquired(qapp, driver, system_driver):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    group = plugin.settings.child('channels')
    group.addNew('Dev2/ai3')
    group.addNew('Dev2/ai1')
    dte = grab_and_wait(plugin)
    assert dte[0].labels == ['Dev2/ai3', 'Dev2/ai1']
    assert [name for _, name, _ in driver[-1].channels] == ['Dev2/ai3', 'Dev2/ai1']
    plugin.close()


def test_the_tree_offers_the_channels_of_the_computer_not_yet_added(qapp, driver, system_driver):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    group = plugin.settings.child('channels')
    assert 'Dev2/ai3' in group.opts['addList']
    group.addNew('Dev2/ai3')
    assert 'Dev2/ai3' not in group.opts['addList']
    plugin.close()


def test_changing_the_type_of_a_channel_changes_the_channel_acquired(qapp, driver, system_driver):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    group = plugin.settings.child('channels')
    group.addNew('Dev2/ai3')
    group.child('Dev2_ai3', 'type').setValue('thermocouple')  # the tree is rebuilt by the plugin
    plugin.commit_settings(group.child('Dev2_ai3', 'type'))
    assert group.child('Dev2_ai3').child('thermocouple_type') is not None
    grab_and_wait(plugin)
    assert driver[-1].channels[0][0] == 'ai_thermocouple'
    plugin.close()


def test_the_1d_generic_viewer_gives_the_trace_of_its_channels(qapp, driver, system_driver):
    from pymodaq_plugins_daqmx.daq_viewer_plugins.plugins_1D.daq_1Dviewer_NIDAQmx import DAQ_1DViewer_NIDAQmx
    plugin = make_detector(DAQ_1DViewer_NIDAQmx, Nsamples=10)
    plugin.settings.child('channels').addNew('Dev2/ai3')
    dte = grab_and_wait(plugin)
    assert dte[0].dim == 'Data1D' and dte[0].data[0].shape == (10,)
    assert dte[0].labels == ['Dev2/ai3']
    plugin.close()


def test_without_channel_the_plugin_initializes_without_task_and_acquires_once_a_channel_is_added(
        qapp, driver, system_driver):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    assert plugin.initialized and driver == []  # nothing to configure yet: no task
    plugin.grab_data()  # no channel: a message, not an exception
    assert driver == []
    plugin.settings.child('channels').addNew('Dev2/ai3')
    dte = grab_and_wait(plugin)
    assert dte[0].labels == ['Dev2/ai3']
    plugin.close()


def test_each_module_is_acquired_by_its_own_task_and_gives_its_own_data(qapp, driver, system_driver):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    group = plugin.settings.child('channels')
    group.addNew('Dev1/ai0')
    group.addNew('Dev2/ai3')
    group.addNew('Dev1/ai1')
    dte = grab_and_wait(plugin)
    assert [task.channels[0][1] for task in driver] == ['Dev1/ai0', 'Dev2/ai3']  # one task per module
    assert [name for _, name, _ in driver[0].channels] == ['Dev1/ai0', 'Dev1/ai1']
    assert [data.labels for data in dte] == [['Dev1/ai0', 'Dev1/ai1'], ['Dev2/ai3']]
    assert [data.name for data in dte] == ['NI AI Dev1', 'NI AI Dev2']
    plugin.close()














def test_a_channel_that_is_not_read_stays_in_the_task_but_not_in_the_data(qapp, driver, system_driver):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    group = plugin.settings.child('channels')
    group.addNew('Dev1/ai0')
    group.addNew('Dev1/ai1')
    group.addNew('Dev2/ai3')
    assert group.child('Dev1_ai1', 'read').value() is True  # read by default
    group.child('Dev1_ai1', 'read').setValue(False)
    plugin.commit_settings(group.child('Dev1_ai1', 'read'))
    dte = grab_and_wait(plugin)
    assert [name for _, name, _ in driver[0].channels] == ['Dev1/ai0', 'Dev1/ai1']  # the task has it (a trigger)
    assert [data.labels for data in dte] == [['Dev1/ai0'], ['Dev2/ai3']]
    plugin.close()


def test_a_module_without_channel_to_read_gives_no_data(qapp, driver, system_driver):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    group = plugin.settings.child('channels')
    group.addNew('Dev1/ai0')
    group.addNew('Dev2/ai3')
    group.child('Dev1_ai0', 'read').setValue(False)
    dte = grab_and_wait(plugin)
    assert [data.labels for data in dte] == [['Dev2/ai3']]
    plugin.close()


def test_changing_the_type_of_a_channel_keeps_whether_it_is_read(qapp, driver, system_driver):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    group = plugin.settings.child('channels')
    group.addNew('Dev1/ai0')
    group.child('Dev1_ai0', 'read').setValue(False)
    group.child('Dev1_ai0', 'type').setValue('current')
    plugin.commit_settings(group.child('Dev1_ai0', 'type'))
    assert group.child('Dev1_ai0', 'read').value() is False
    plugin.close()


def two_modules(plugin, display=None):
    group = plugin.settings.child('channels')
    group.addNew('Dev1/ai0')
    group.addNew('Dev2/ai3')
    plugin.commit_settings(group)
    return plugin.settings.child('modules')


def test_each_module_has_its_own_settings_that_start_at_the_defaults(qapp, driver, system_driver):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    modules = two_modules(plugin)
    assert [child.name() for child in modules.children()] == ['Dev1', 'Dev2']
    assert modules['Dev1', 'frequency'] == 1000 and modules['Dev1', 'clock'] == 'internal'
    assert modules['Dev1', 'trigger', 'type'] == 'none'
    modules.child('Dev2', 'frequency').setValue(500)
    plugin.commit_settings(modules.child('Dev2', 'frequency'))
    grab_and_wait(plugin)
    assert [task.timing_calls[0][1] for task in driver] == [1000, 500]
    plugin.settings.child('channels').removeChild(plugin.settings.child('channels', 'Dev1_ai0'))
    plugin.commit_settings(plugin.settings.child('channels'))
    assert [child.name() for child in modules.children()] == ['Dev2']
    plugin.close()


def test_a_digital_edge_trigger_starts_the_task_of_its_module_only(qapp, driver, system_driver):
    from nidaqmx.constants import Edge
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    modules = two_modules(plugin)
    trigger = modules.child('Dev1', 'trigger')
    trigger.child('type').setValue('digital edge')
    plugin.commit_settings(trigger.child('type'))
    assert trigger.child('terminal').opts['visible'] and not trigger.child('level').opts['visible']
    trigger.child('terminal').setValue('/Dev1/PFI1')
    trigger.child('edge').setValue('falling')
    grab_and_wait(plugin)
    assert [task.trigger_calls for task in driver] == [[('dig_edge', '/Dev1/PFI1', Edge.FALLING)], []]
    plugin.close()


def test_an_analog_edge_trigger_watches_a_channel_or_an_apfi_terminal_of_its_own_module(qapp, driver, system_driver):
    from nidaqmx.constants import Slope
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    modules = two_modules(plugin)
    trigger = modules.child('Dev2', 'trigger')
    trigger.child('type').setValue('analog edge')
    plugin.commit_settings(trigger.child('type'))
    assert trigger.child('channel').opts['visible'] and not trigger.child('terminal').opts['visible']
    assert trigger.child('channel').opts['limits'] == ['Dev2/ai3', '/Dev2/APFI0', '/Dev2/APFI1']
    trigger.child('channel').setValue('/Dev2/APFI0')
    trigger.child('level').setValue(1.5)
    grab_and_wait(plugin)
    assert [task.trigger_calls for task in driver] == [[], [('anlg_edge', '/Dev2/APFI0', Slope.RISING, 1.5)]]
    plugin.close()


def test_a_module_can_be_timed_by_the_clock_of_another_which_then_starts_last(qapp, driver, system_driver):
    from nidaqmx_double import DoubleTask
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    modules = two_modules(plugin)
    clock = modules.child('Dev2', 'clock')
    assert '/Dev1/ai/SampleClock' in clock.opts['limits'] and '/Dev2/ai/SampleClock' not in clock.opts['limits']
    clock.setValue('/Dev1/ai/SampleClock')
    grab_and_wait(plugin)
    assert [call[2]['source'] for call in (task.timing_calls[0] for task in driver)] == ['', '/Dev1/ai/SampleClock']
    starts = [name for what, name in DoubleTask.log if what == 'start']
    assert starts == ['Dev2/ai3', 'Dev1/ai0']  # the one that waits for the clock is armed before the one that gives it
    plugin.close()


def test_all_the_modules_can_follow_an_external_clock_in_any_order(qapp, driver, system_driver):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    modules = two_modules(plugin)
    for module in ('Dev1', 'Dev2'):
        modules.child(module, 'clock').setValue('/Dev1/PFI0')
    grab_and_wait(plugin)
    assert [task.timing_calls[0][2]['source'] for task in driver] == ['/Dev1/PFI0'] * 2
    plugin.close()


def test_modules_that_wait_for_each_other_are_refused_with_a_message_naming_them(qapp, driver, system_driver):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    modules = two_modules(plugin)
    modules.child('Dev1', 'clock').setValue('/Dev2/ai/SampleClock')
    modules.child('Dev2', 'clock').setValue('/Dev1/ai/SampleClock')
    with pytest.raises(ValueError, match='Dev1.*Dev2'):
        plugin.grab_data()
    plugin.close()


def test_the_1d_axis_is_in_samples_with_an_external_clock_and_in_seconds_otherwise(qapp, driver, system_driver):
    from pymodaq_plugins_daqmx.daq_viewer_plugins.plugins_1D.daq_1Dviewer_NIDAQmx import DAQ_1DViewer_NIDAQmx
    plugin = make_detector(DAQ_1DViewer_NIDAQmx, Nsamples=10)
    modules = two_modules(plugin)
    modules.child('Dev2', 'frequency').setValue(500)
    modules.child('Dev2', 'clock').setValue('/Dev2/PFI0')
    dte = grab_and_wait(plugin)
    seconds, samples = dte[0].axes[0], dte[1].axes[0]
    assert seconds.get_data()[1] == pytest.approx(1 / 1000) and seconds.units == 's'
    assert list(samples.get_data()[:3]) == [0, 1, 2] and samples.label == 'sample'
    plugin.close()


def test_without_trigger_the_tasks_start_at_once(qapp, driver, system_driver):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    plugin.settings.child('channels').addNew('Dev1/ai0')
    grab_and_wait(plugin)
    assert driver[0].trigger_calls == []
    plugin.close()
