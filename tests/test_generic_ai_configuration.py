"""The configuration menu of the generic NI viewer: channels loaded from, and saved to, the configuration files."""
import shutil
from pathlib import Path

import pytest

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
    assert plugin.settings.child('config', 'module').opts['limits'] == [
        '(all)', 'cDAQ1Mod1', 'cDAQ1Mod2', 'cDAQ1Mod3', 'cDAQ1Mod4']
    group = plugin.settings.child('channels')
    assert [child.opts['title'] for child in group.children()] == [  # (all): the modules in the order of the file
        'cDAQ1Mod1/ai2', 'cDAQ1Mod1/ai1', 'cDAQ1Mod3/ai0', 'cDAQ1Mod3/ai5']
    choose(plugin, 'module', 'cDAQ1Mod3')
    group = plugin.settings.child('channels')
    assert [child.opts['title'] for child in group.children()] == ['cDAQ1Mod3/ai0', 'cDAQ1Mod3/ai5']
    choose(plugin, 'module', 'cDAQ1Mod1')  # the channels of the previous module are replaced
    assert [child.opts['title'] for child in group.children()] == ['cDAQ1Mod1/ai2', 'cDAQ1Mod1/ai1']
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
    choose(plugin, 'configuration', 'mine')  # (all)
    assert sorted(child.opts['title'] for child in group.children()) == ['Dev1/ai1', 'Dev2/ai1', 'Dev2/ai3']
    plugin.close()


def test_saving_into_an_existing_suffix_replaces_the_devices_of_the_tree_and_keeps_the_others(
        qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    plugin.settings.child('channels').addNew('Dev2/ai3')
    plugin.settings.child('config', 'save').opts.update(suffix='lab')
    press(plugin, 'config', 'save')
    saved = ConfigFiles(folder).load('lab')
    assert [channel.name for channel in saved.channels('Dev2')] == ['Dev2/ai3']
    assert [channel.name for channel in saved.channels('cDAQ1Mod3')] == ['cDAQ1Mod3/ai0', 'cDAQ1Mod3/ai5']
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
    choose(plugin, 'module', 'cDAQ1Mod3')
    choose(plugin, 'configuration', 'broken')
    assert (plugin.settings['config', 'configuration'], plugin.settings['config', 'module']) == ('lab', 'cDAQ1Mod3')
    assert [child.opts['title'] for child in plugin.settings.child('channels').children()] == [
        'cDAQ1Mod3/ai0', 'cDAQ1Mod3/ai5']  # and the channels are the ones of that module
    plugin.close()


def test_going_back_to_manual_keeps_the_channels_and_hides_the_module(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    choose(plugin, 'configuration', 'lab')
    choose(plugin, 'configuration', '(manual)')
    assert not plugin.settings.child('config', 'module').opts['visible']
    assert len(plugin.settings.child('channels').children()) == 4  # the channels of (all) stay
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
