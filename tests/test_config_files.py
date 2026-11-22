"""The configuration files that describe the channels of the modules of a bench."""
import shutil
from pathlib import Path

import pytest
import toml
from nidaqmx.constants import TemperatureUnits, TerminalConfiguration, ThermocoupleType

from pymodaq_plugins_daqmx.hardware.national_instruments.api import AIThermocouple, AIVoltage
from pymodaq_plugins_daqmx.hardware.national_instruments.config_files import ConfigFileError, ConfigFiles

DATA = Path(__file__).parent / 'data'


@pytest.fixture
def folder(tmp_path):
    """A configuration folder holding the file of a real bench, as the default configuration."""
    shutil.copy(DATA / 'config_daqmx_bench.toml', tmp_path / 'config_daqmx.toml')
    return tmp_path


def test_channels_of_a_module_come_as_api_channels(folder):
    config = ConfigFiles(folder).load('')

    # in the order of the file: it is the order of the data of an acquisition
    assert config.channels('cDAQ1Mod1') == [
        AIThermocouple('cDAQ1Mod1/ai2', thermocouple_type=ThermocoupleType.K, units=TemperatureUnits.DEG_C,
                       min_val=0., max_val=50.),
        AIThermocouple('cDAQ1Mod1/ai1', thermocouple_type=ThermocoupleType.K, units=TemperatureUnits.DEG_C,
                       min_val=0., max_val=50.)]
    assert config.channels('cDAQ1Mod3') == [
        AIVoltage('cDAQ1Mod3/ai0', min_val=-10., max_val=10., terminal_config=TerminalConfiguration.RSE),
        AIVoltage('cDAQ1Mod3/ai5', min_val=-10., max_val=10., terminal_config=TerminalConfiguration.RSE)]


def test_the_configurations_to_choose_from_are_the_suffixes_of_the_files(folder):
    shutil.copy(DATA / 'config_daqmx_bench.toml', folder / 'config_daqmx_laser_bench.toml')
    (folder / 'config_other.toml').write_text('')   # not ours
    (folder / 'notes.txt').write_text('')

    assert ConfigFiles(folder).suffixes() == ['', 'laser_bench']


def test_there_is_no_configuration_in_an_empty_folder(tmp_path):
    assert ConfigFiles(tmp_path).suffixes() == []


def test_a_saved_configuration_loads_back_with_the_same_channels(folder):
    files = ConfigFiles(folder)
    config = files.load('')

    files.save('copy', config)

    assert files.suffixes() == ['', 'copy']
    reloaded = files.load('copy')
    for module in ('cDAQ1Mod1', 'cDAQ1Mod3'):
        assert reloaded.channels(module) == config.channels(module)


def test_a_saved_file_keeps_the_layout_and_the_notes_of_the_original(folder):
    files = ConfigFiles(folder)

    files.save('copy', files.load(''))

    saved = toml.loads(files.path('copy').read_text())
    original = toml.loads(files.path('').read_text())
    assert saved['NIDAQ_Devices']['DEVICE01']['product'] == 'cDAQ-9174'
    assert saved['NIDAQ_Devices']['DEVICE01']['MODULE03']['product'] == 'NI 9205'
    assert saved['NIDAQ_Devices']['DEVICE01']['MODULE03']['ai'] == original['NIDAQ_Devices']['DEVICE01']['MODULE03']['ai']
    assert saved['NIDAQ_Devices']['DEVICE01']['MODULE01']['ai'] == original['NIDAQ_Devices']['DEVICE01']['MODULE01']['ai']


def _bench_with(tmp_path, old, new):
    """A copy of the bench file where ``old`` is replaced by ``new``."""
    text = (DATA / 'config_daqmx_bench.toml').read_text()
    assert old in text
    (tmp_path / 'config_daqmx.toml').write_text(text.replace(old, new, 1))
    return ConfigFiles(tmp_path)


@pytest.mark.parametrize('old, new, where, why', [
    ('analog_type = "VOLTAGE"', 'analog_type = "FLUX"', 'cDAQ1Mod3.ai.ai0', "analog_type 'FLUX'"),
    ('termination = "RSE"', 'termination = "FLOATING"', 'cDAQ1Mod3.ai.ai0', "termination 'FLOATING'"),
    ('thermo_type = "K"', 'thermo_type = "Z"', 'cDAQ1Mod1.ai.ai2', "thermo_type 'Z'"),
    ('value_max = 10.0', 'value_max = -20.0', 'cDAQ1Mod3.ai.ai0', 'must be lower than'),
    ('termination = "RSE"', 'comment = "no termination here"', 'cDAQ1Mod3.ai.ai0', "'termination'"),
])
def test_a_wrong_entry_is_reported_with_the_file_and_the_channel(tmp_path, old, new, where, why):
    files = _bench_with(tmp_path, old, new)

    with pytest.raises(ConfigFileError) as error:
        files.load('')

    message = str(error.value)
    assert 'config_daqmx.toml' in message and where in message and why in message


def test_a_file_that_is_not_toml_is_reported_with_its_path(tmp_path):
    (tmp_path / 'config_daqmx_broken.toml').write_text('[NIDAQ_Devices\nname = ')

    with pytest.raises(ConfigFileError, match='config_daqmx_broken.toml'):
        ConfigFiles(tmp_path).load('broken')
