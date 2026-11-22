"""The configuration menu of the generic NI viewer: channels loaded from, and saved to, the configuration files."""
import shutil
from pathlib import Path

import pytest
from easydict import EasyDict as edict
from pyqtgraph.parametertree import Parameter

from pymodaq_gui.parameter import pymodaq_ptypes, utils as putils  # noqa: F401  (the types are registered)

pytest.importorskip('nidaqmx')
pytest.importorskip('pymodaq')

from pymodaq.utils.plugin_testing import make_detector, grab_and_wait

from pymodaq_plugins_daqmx.daq_viewer_plugins.plugins_0D.daq_0Dviewer_NIDAQmx import DAQ_0DViewer_NIDAQmx
from pymodaq_plugins_daqmx.hardware.national_instruments import config_files
from pymodaq_plugins_daqmx.hardware.national_instruments.config_files import ConfigFiles

from nidaqmx_double import driver, system_driver  # noqa: F401  (pytest fixtures)

DATA = Path(__file__).parent / 'data'


@pytest.fixture
def folder(tmp_path, monkeypatch):
    """The system folder of the configuration files, with the bench as the default configuration and as ``lab``."""
    shutil.copy(DATA / 'config_daqmx_bench.toml', tmp_path / 'config_daqmx.toml')
    shutil.copy(DATA / 'config_daqmx_bench_v1.toml', tmp_path / 'config_daqmx_lab.toml')
    monkeypatch.setattr(config_files, 'system_folder', lambda: tmp_path)
    return tmp_path


def choose(plugin, name, value):
    param = plugin.settings.child('config', name)
    param.setValue(value)
    plugin.commit_settings(param)


def capture(plugin):
    """What the plugin tells the control module (apart from the sync of the tree) is collected in the list."""
    sent = []
    plugin.emit_status = lambda status: status.command != 'update_settings' and sent.append(status)
    return sent


def press(plugin, *path):
    """Press an action button of the settings; what the plugin tells the control module is returned."""
    sent = capture(plugin)
    plugin.commit_settings(plugin.settings.child(*path))  # what the plugin does when the GUI activates the button
    return sent


def test_the_menu_offers_a_manual_choice_and_the_files_of_the_folder(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    menu = plugin.settings.child('config', 'configuration')
    assert menu.value() == '(manual)'
    assert menu.opts['limits'] == ['(manual)', 'default', 'lab']
    plugin.close()


def test_choosing_a_configuration_fills_the_channels_in_the_order_of_the_file_and_tells_the_control_module(
        qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    sent = capture(plugin)
    choose(plugin, 'configuration', 'lab')
    assert [status.command for status in sent] == ['Update_Status']
    assert 'lab' in sent[0].attribute[0]
    group = plugin.settings.child('channels')
    assert [child.opts['title'] for child in group.children()] == [
        'cDAQ1Mod1/ai2', 'cDAQ1Mod1/ai1', 'cDAQ1Mod3/ai0', 'cDAQ1Mod3/ai5']
    plugin.close()


def test_saving_puts_each_channel_in_the_module_of_its_device_so_that_devices_can_be_mixed(
        qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    group = plugin.settings.child('channels')
    for name in ('Dev2/ai3', 'Dev1/ai1', 'Dev2/ai1', 'Dev2/ai0'):
        group.addNew(name)
    plugin.settings.child('config', 'save').opts.update(suffix='mine')
    sent = press(plugin, 'config', 'save')
    assert [status.command for status in sent] == ['Update_Status']
    assert plugin.settings['config', 'save'] == 'idle'  # the LED of the button
    saved = ConfigFiles(folder).load('mine')
    assert list(saved.modules) == ['Dev2', 'Dev1']
    assert [channel.name for channel in saved.channels('Dev2')] == ['Dev2/ai3', 'Dev2/ai1', 'Dev2/ai0']
    assert [channel.name for channel in saved.channels('Dev1')] == ['Dev1/ai1']
    assert plugin.settings.child('config', 'configuration').opts['limits'] == ['(manual)', 'default', 'lab', 'mine']
    plugin.close()


def test_what_is_saved_is_loaded_back_as_it_was(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    group = plugin.settings.child('channels')
    for name in ('Dev2/ai3', 'Dev1/ai1', 'Dev2/ai1'):
        group.addNew(name)
    plugin.settings.child('config', 'save').opts.update(suffix='mine')
    press(plugin, 'config', 'save')
    group.setChannels([])
    choose(plugin, 'configuration', 'mine')
    assert sorted(child.opts['title'] for child in group.children()) == ['Dev1/ai1', 'Dev2/ai1', 'Dev2/ai3']
    plugin.close()


def test_saving_into_an_existing_suffix_makes_the_file_describe_the_channels_of_the_tree(
        qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    plugin.settings.child('channels').addNew('Dev2/ai3')
    plugin.settings.child('config', 'save').opts.update(suffix='lab')
    press(plugin, 'config', 'save')
    saved = ConfigFiles(folder).load('lab')
    assert list(saved.modules) == ['Dev2']  # what is not in the tree is not in the file any more
    assert [channel.name for channel in saved.channels('Dev2')] == ['Dev2/ai3']
    plugin.close()


def test_a_file_that_cannot_be_read_puts_the_control_module_in_error_with_the_file_named(
        qapp, driver, system_driver, folder):
    (folder / 'config_daqmx_broken.toml').write_text('version = 1\n[modules.M.ai.x]\ntype = "nothing"\n')
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    sent = capture(plugin)
    choose(plugin, 'configuration', 'broken')
    assert [status.command for status in sent] == ['error']
    assert 'config_daqmx_broken.toml' in sent[0].attribute
    plugin.close()


def test_after_a_failed_load_the_menu_shows_the_configuration_really_loaded(qapp, driver, system_driver, folder):
    (folder / 'config_daqmx_broken.toml').write_text('version = 1\n[modules.M.ai.x]\ntype = "nothing"\n')
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    choose(plugin, 'configuration', 'broken')
    assert plugin.settings['config', 'configuration'] == '(manual)'  # nothing was loaded before
    choose(plugin, 'configuration', 'lab')
    choose(plugin, 'configuration', 'broken')
    assert plugin.settings['config', 'configuration'] == 'lab'
    assert len(plugin.settings.child('channels').children()) == 4  # and the channels are the ones of that file
    plugin.close()


def test_going_back_to_manual_keeps_the_channels(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    choose(plugin, 'configuration', 'lab')
    choose(plugin, 'configuration', '(manual)')
    assert len(plugin.settings.child('channels').children()) == 4
    plugin.close()


def test_the_dialog_proposes_the_configuration_that_is_loaded(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    choose(plugin, 'configuration', 'lab')
    assert plugin.settings.child('config', 'save').opts['suffix'] == 'lab'
    plugin.close()


def test_a_save_that_fails_puts_the_led_of_the_button_in_error(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    sent = press(plugin, 'config', 'save')  # no channel to save
    assert [status.command for status in sent] == ['error']
    assert plugin.settings['config', 'save'] == 'error'
    plugin.close()


def test_the_led_of_the_save_button_starts_off(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    assert plugin.settings['config', 'save'] == 'off'
    plugin.close()


def gui_copy(plugin):
    """The settings tree of the GUI: the same parameters in other objects, as the control module holds them."""
    return Parameter.create(name=plugin.settings.name(), type='group', children=DAQ_0DViewer_NIDAQmx.params)


def from_gui(plugin, gui, *path, value=None):
    """What the control module does when the user changes a parameter in the GUI: the plugin receives the copy."""
    param = gui.child(*path)
    if value is not None:
        param.setValue(value)
    plugin.update_settings(edict(path=putils.get_param_path(param), param=param, change='value'))


def test_a_configuration_chosen_in_the_gui_is_loaded_in_the_tree_of_the_plugin(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    gui = gui_copy(plugin)
    from_gui(plugin, gui, 'config', 'configuration', value='lab')
    assert len(plugin.settings.child('channels').children()) == 4
    assert plugin.settings['config', 'configuration'] == 'lab'
    plugin.close()


def test_a_type_changed_in_the_gui_rebuilds_the_channel_of_the_tree_of_the_plugin(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    plugin.settings.child('channels').addNew('Dev2/ai3')
    gui = gui_copy(plugin)
    gui.child('channels').addNew('Dev2/ai3')
    from_gui(plugin, gui, 'channels', 'Dev2_ai3', 'type', value='thermocouple')
    assert plugin.settings.child('channels', 'Dev2_ai3').child('thermocouple_type') is not None
    plugin.close()


def test_the_save_button_activated_in_the_gui_saves_with_the_suffix_of_its_dialog(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    plugin.settings.child('channels').addNew('Dev2/ai3')
    gui = gui_copy(plugin)
    button = gui.child('config', 'save')
    button.opts['suffix'] = 'fromgui'  # what the dialog returned
    plugin.update_settings(edict(path=putils.get_param_path(button), param=button, change='activated'))
    assert [c.name for c in ConfigFiles(folder).load('fromgui').channels('Dev2')] == ['Dev2/ai3']
    assert plugin.settings['config', 'save'] == 'idle'
    plugin.close()


def led(plugin):
    return plugin.settings['config', 'reload']


def test_the_reload_led_tells_whether_the_tree_is_the_loaded_file(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    assert led(plugin) == 'off'  # (manual): nothing to compare with
    choose(plugin, 'configuration', 'lab')
    assert led(plugin) == 'idle'  # the tree is the file
    group = plugin.settings.child('channels')
    group.removeChild(group.child('cDAQ1Mod1_ai2'))
    plugin.commit_settings(group)  # what the plugin does when the GUI removes a channel
    assert led(plugin) == 'warning'
    plugin.close()


def test_a_value_changed_in_a_channel_makes_the_led_warn_and_changing_it_back_makes_it_idle_again(
        qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    choose(plugin, 'configuration', 'lab')
    value = plugin.settings.child('channels', 'cDAQ1Mod3_ai0', 'min_val')
    previous = value.value()
    value.setValue(previous + 1)
    plugin.commit_settings(value)
    assert led(plugin) == 'warning'
    value.setValue(previous)
    plugin.commit_settings(value)
    assert led(plugin) == 'idle'
    plugin.close()


def test_reload_puts_back_the_channels_of_the_file(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    choose(plugin, 'configuration', 'lab')
    group = plugin.settings.child('channels')
    group.removeChild(group.child('cDAQ1Mod1_ai2'))
    gui = gui_copy(plugin)
    button = gui.child('config', 'reload')
    plugin.update_settings(edict(path=putils.get_param_path(button), param=button, change='activated'))
    assert len(group.children()) == 4
    assert led(plugin) == 'idle'
    plugin.close()


def test_reload_without_configuration_only_says_so(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    plugin.settings.child('channels').addNew('Dev2/ai3')
    sent = press(plugin, 'config', 'reload')
    assert [status.command for status in sent] == ['Update_Status']
    assert len(plugin.settings.child('channels').children()) == 1  # nothing is replaced
    assert led(plugin) == 'off'
    plugin.close()


def test_after_a_save_the_menu_shows_the_file_that_was_just_written(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    choose(plugin, 'configuration', 'lab')
    plugin.settings.child('channels').addNew('Dev2/ai3')
    plugin.settings.child('config', 'save').opts.update(suffix='second')
    press(plugin, 'config', 'save')
    assert plugin.settings['config', 'configuration'] == 'second'  # the tree is that file now
    assert led(plugin) == 'idle'
    plugin.close()


def test_a_value_that_is_not_a_configuration_is_ignored(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    choose(plugin, 'configuration', 'lab')
    sent = capture(plugin)
    param = plugin.settings.child('config', 'configuration')
    param.opts['value'] = None  # what a combo that is being rebuilt sends
    plugin.commit_settings(param)
    assert sent == []
    assert len(plugin.settings.child('channels').children()) == 4
    plugin.close()
