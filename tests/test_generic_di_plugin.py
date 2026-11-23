"""Behaviour of the generic NI digital input viewer (1D traces of lines, no hardware needed)."""
import pytest

pytest.importorskip('nidaqmx')
pytest.importorskip('pymodaq')

from pymodaq.utils.plugin_testing import make_detector, grab_and_wait

from pymodaq_plugins_daqmx.daq_viewer_plugins.plugins_1D.daq_1Dviewer_NIDAQmx_DI import DAQ_1DViewer_NIDAQmx_DI

from nidaqmx_double import driver, system_driver  # noqa: F401  (pytest fixtures)


def test_the_tree_offers_the_digital_lines_of_the_computer(qapp, driver, system_driver):
    plugin = make_detector(DAQ_1DViewer_NIDAQmx_DI, Nsamples=10)
    group = plugin.settings.child('channels')
    assert 'Dev1/port0/line0' in group.opts['addList'] and not [n for n in group.opts['addList'] if '/ai' in n]
    plugin.close()


def test_the_lines_added_to_the_tree_give_a_trace_each(qapp, driver, system_driver):
    plugin = make_detector(DAQ_1DViewer_NIDAQmx_DI, Nsamples=10)
    group = plugin.settings.child('channels')
    group.addNew('Dev2/port0/line1')
    group.addNew('Dev2/port0/line0')
    dte = grab_and_wait(plugin)
    assert dte[0].dim == 'Data1D' and dte[0].name == 'NI DI Dev2'
    assert dte[0].labels == ['Dev2/port0/line1', 'Dev2/port0/line0']
    assert [d.shape for d in dte[0].data] == [(10,), (10,)]
    # in the double, the line of row c is high at the samples s with c + s even
    assert [d.tolist() for d in dte[0].data] == [[1., 0.] * 5, [0., 1.] * 5]
    assert [kind for kind, *_ in driver[-1].channels] == ['di', 'di']
    plugin.close()


def test_each_module_has_its_own_clocked_task_and_digital_trigger_only(qapp, driver, system_driver):
    from nidaqmx.constants import Edge
    plugin = make_detector(DAQ_1DViewer_NIDAQmx_DI, Nsamples=10)
    group = plugin.settings.child('channels')
    group.addNew('Dev1/port0/line0')
    group.addNew('Dev2/port0/line0')
    plugin.commit_settings(group)
    modules = plugin.settings.child('modules')
    assert modules.child('Dev1', 'trigger', 'type').opts['limits'] == ['none', 'digital edge']
    modules['Dev1', 'frequency'] = 500
    trigger = modules.child('Dev1', 'trigger')
    trigger.child('type').setValue('digital edge')
    plugin.commit_settings(trigger.child('type'))
    trigger.child('terminal').setValue('/Dev1/PFI1')
    dte = grab_and_wait(plugin)
    assert [d.name for d in dte] == ['NI DI Dev1', 'NI DI Dev2']
    assert driver[0].timing_calls[0][1] == 500 and driver[1].timing_calls[0][1] == 1000
    assert driver[0].trigger_calls == [('dig_edge', '/Dev1/PFI1', Edge.RISING)] and driver[1].trigger_calls == []
    assert dte[0].axes[0].units == 's'
    plugin.close()


def test_the_digital_viewer_has_no_live_mode_nor_configuration_menu(qapp, driver, system_driver):
    plugin = make_detector(DAQ_1DViewer_NIDAQmx_DI)
    assert not plugin.live_mode_available
    assert 'config' not in plugin.settings.names
    plugin.close()
