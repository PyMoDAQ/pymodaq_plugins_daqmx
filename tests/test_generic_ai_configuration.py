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
    param = plugin.settings.child(name)
    param.setValue(value)
    plugin.commit_settings(param)


def test_the_menu_offers_a_manual_choice_and_the_files_of_the_folder(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    menu = plugin.settings.child('configuration')
    assert menu.value() == '(manual)'
    assert menu.opts['limits'] == ['(manual)', 'default', 'lab']
    plugin.close()


def test_choosing_a_configuration_and_a_module_fills_the_channels_in_the_order_of_the_file(
        qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    choose(plugin, 'configuration', 'lab')
    assert plugin.settings.child('module').opts['limits'] == ['cDAQ1Mod1', 'cDAQ1Mod2', 'cDAQ1Mod3', 'cDAQ1Mod4']
    choose(plugin, 'module', 'cDAQ1Mod3')
    group = plugin.settings.child('channels')
    assert [child.opts['title'] for child in group.children()] == ['cDAQ1Mod3/ai0', 'cDAQ1Mod3/ai5']
    choose(plugin, 'module', 'cDAQ1Mod1')  # the channels of the previous module are replaced
    assert [child.opts['title'] for child in group.children()] == ['cDAQ1Mod1/ai2', 'cDAQ1Mod1/ai1']
    plugin.close()


def test_saving_under_a_suffix_writes_the_channels_of_the_tree(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    group = plugin.settings.child('channels')
    group.addNew('Dev2/ai3')
    group.addNew('Dev2/ai1')
    plugin.settings.child('save', 'module').setValue('Dev2')
    plugin.settings.child('save', 'suffix').setValue('mine')
    choose_param = plugin.settings.child('save', 'save')
    choose_param.setValue(True)
    plugin.commit_settings(choose_param)
    saved = ConfigFiles(folder).load('mine')
    assert [channel.name for channel in saved.channels('Dev2')] == ['Dev2/ai3', 'Dev2/ai1']
    assert plugin.settings.child('configuration').opts['limits'] == ['(manual)', 'default', 'lab', 'mine']
    plugin.close()


def test_saving_into_an_existing_suffix_keeps_the_other_modules_of_the_file(qapp, driver, system_driver, folder):
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    plugin.settings.child('channels').addNew('Dev2/ai3')
    plugin.settings.child('save', 'module').setValue('Dev2')
    plugin.settings.child('save', 'suffix').setValue('lab')
    param = plugin.settings.child('save', 'save')
    param.setValue(True)
    plugin.commit_settings(param)
    saved = ConfigFiles(folder).load('lab')
    assert [channel.name for channel in saved.channels('Dev2')] == ['Dev2/ai3']
    assert [channel.name for channel in saved.channels('cDAQ1Mod3')] == ['cDAQ1Mod3/ai0', 'cDAQ1Mod3/ai5']
    assert param.value() is False  # the button is released
    plugin.close()


def test_a_file_that_cannot_be_read_is_an_error_naming_it(qapp, driver, system_driver, folder):
    (folder / 'config_daqmx_broken.toml').write_text('version = 1\n[modules.M.ai.x]\ntype = "nothing"\n')
    plugin = make_detector(DAQ_0DViewer_NIDAQmx)
    with pytest.raises(config_files.ConfigFileError, match='config_daqmx_broken.toml'):
        choose(plugin, 'configuration', 'broken')
    plugin.close()
