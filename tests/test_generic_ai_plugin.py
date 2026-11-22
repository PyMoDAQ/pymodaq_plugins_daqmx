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
