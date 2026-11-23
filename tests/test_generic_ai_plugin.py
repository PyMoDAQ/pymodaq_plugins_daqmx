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


def test_each_module_has_its_own_frequency_that_starts_at_the_global_one(qapp, driver, system_driver):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    group = plugin.settings.child('channels')
    group.addNew('Dev1/ai0')
    group.addNew('Dev2/ai3')
    plugin.commit_settings(group)
    frequencies = plugin.settings.child('frequencies')
    assert [(c.name(), c.value()) for c in frequencies.children()] == [('Dev1', 1000), ('Dev2', 1000)]
    frequencies.child('Dev2').setValue(500)
    plugin.commit_settings(frequencies.child('Dev2'))
    grab_and_wait(plugin)
    assert [task.timing_calls[0][1] for task in driver] == [1000, 500]
    group.removeChild(group.child('Dev1_ai0'))
    plugin.commit_settings(group)
    assert [c.name() for c in frequencies.children()] == ['Dev2']
    plugin.close()


def test_the_1d_viewer_gives_a_trace_per_module_at_the_frequency_of_the_module(qapp, driver, system_driver):
    from pymodaq_plugins_daqmx.daq_viewer_plugins.plugins_1D.daq_1Dviewer_NIDAQmx import DAQ_1DViewer_NIDAQmx
    plugin = make_detector(DAQ_1DViewer_NIDAQmx, Nsamples=10)
    group = plugin.settings.child('channels')
    group.addNew('Dev1/ai0')
    group.addNew('Dev2/ai3')
    plugin.commit_settings(group)
    plugin.settings.child('frequencies', 'Dev2').setValue(500)
    dte = grab_and_wait(plugin)
    assert [data.dim for data in dte] == ['Data1D', 'Data1D']
    assert [data.axes[0].get_data()[1] for data in dte] == pytest.approx([1 / 1000, 1 / 500])
    plugin.close()


def test_a_digital_edge_trigger_starts_every_task(qapp, driver, system_driver):
    from nidaqmx.constants import Edge
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    group = plugin.settings.child('channels')
    group.addNew('Dev1/ai0')
    group.addNew('Dev2/ai3')
    trigger = plugin.settings.child('trigger')
    trigger.child('type').setValue('digital edge')
    plugin.commit_settings(trigger.child('type'))
    assert trigger.child('terminal').opts['visible'] and not trigger.child('level').opts['visible']
    trigger.child('terminal').setValue('/Dev1/PFI1')
    trigger.child('edge').setValue('falling')
    grab_and_wait(plugin)
    assert [task.trigger_calls for task in driver] == [[('dig_edge', '/Dev1/PFI1', Edge.FALLING)]] * 2
    plugin.close()


def test_an_analog_edge_trigger_waits_for_the_level_of_a_channel_of_the_tree_and_starts_the_task_of_its_module(
        qapp, driver, system_driver):
    from nidaqmx.constants import Slope
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    group = plugin.settings.child('channels')
    group.addNew('Dev1/ai0')
    group.addNew('Dev1/ai1')
    group.addNew('Dev2/ai3')
    plugin.commit_settings(group)
    trigger = plugin.settings.child('trigger')
    trigger.child('type').setValue('analog edge')
    plugin.commit_settings(trigger.child('type'))
    assert trigger.child('channel').opts['visible'] and not trigger.child('terminal').opts['visible']
    assert trigger.child('channel').opts['limits'][:3] == ['Dev1/ai0', 'Dev1/ai1', 'Dev2/ai3']  # the channels first
    trigger.child('channel').setValue('Dev1/ai1')
    trigger.child('level').setValue(1.5)
    grab_and_wait(plugin)
    assert [task.trigger_calls for task in driver] == [[('anlg_edge', 'Dev1/ai1', Slope.RISING, 1.5)], []]
    plugin.close()


def test_without_trigger_the_tasks_start_at_once(qapp, driver, system_driver):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    plugin.settings.child('channels').addNew('Dev1/ai0')
    grab_and_wait(plugin)
    assert driver[0].trigger_calls == []
    plugin.close()


def test_a_dedicated_analog_trigger_terminal_can_be_the_source_and_starts_the_task_of_its_device(
        qapp, driver, system_driver):
    from nidaqmx.constants import Slope
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    group = plugin.settings.child('channels')
    group.addNew('Dev1/ai0')
    group.addNew('Dev2/ai3')
    plugin.commit_settings(group)
    trigger = plugin.settings.child('trigger')
    trigger.child('type').setValue('analog edge')
    plugin.commit_settings(trigger.child('type'))
    assert trigger.child('channel').opts['limits'] == ['Dev1/ai0', 'Dev2/ai3', '/Dev2/APFI0', '/Dev2/APFI1']
    trigger.child('channel').setValue('/Dev2/APFI0')
    grab_and_wait(plugin)
    assert [task.trigger_calls for task in driver] == [[], [('anlg_edge', '/Dev2/APFI0', Slope.RISING, 0.)]]
    plugin.close()
