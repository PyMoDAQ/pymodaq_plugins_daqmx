"""The configuration files that describe the channels of the modules of a bench."""
import shutil
from pathlib import Path

import pytest
import toml
from nidaqmx.constants import (ResistanceConfiguration, RTDType, TemperatureUnits, TerminalConfiguration,
                               ThermocoupleType)

from pymodaq_plugins_daqmx.hardware.national_instruments.api import AICurrent, AIRtd, AIThermocouple, AIVoltage
from pymodaq_plugins_daqmx.hardware.national_instruments.config_files import Configuration, ConfigFileError, ConfigFiles

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


def test_the_current_format_gives_the_same_channels_as_the_previous_one(folder):
    shutil.copy(DATA / 'config_daqmx_bench_v1.toml', folder / 'config_daqmx_v1.toml')
    files = ConfigFiles(folder)

    for module in ('cDAQ1Mod1', 'cDAQ1Mod2', 'cDAQ1Mod3', 'cDAQ1Mod4'):
        assert files.load('v1').channels(module) == files.load('').channels(module)


def test_saving_a_previous_file_writes_the_current_format_and_keeps_everything(folder):
    files = ConfigFiles(folder)

    files.save('copy', files.load(''))

    saved = toml.loads(files.path('copy').read_text())
    expected = toml.loads((DATA / 'config_daqmx_bench_v1.toml').read_text())
    saved.pop('description'), expected.pop('description')
    assert saved == expected


def test_a_saved_file_loads_back_with_the_same_channels_and_notes(folder):
    files = ConfigFiles(folder)
    files.save('copy', files.load(''))

    files.save('again', files.load('copy'))

    assert files.path('again').read_text() == files.path('copy').read_text()


def test_every_analog_input_type_survives_a_round_trip(tmp_path):
    channels = [AIVoltage('Dev1/ai0', -5., 5., TerminalConfiguration.DIFF),
                AICurrent('Dev1/ai1', -0.02, 0.02, TerminalConfiguration.RSE),
                AIThermocouple('Dev1/ai2', ThermocoupleType.J, TemperatureUnits.DEG_F, 10., 200.),
                AIRtd('Dev1/ai3', RTDType.PT_3750, ResistanceConfiguration.FOUR_WIRE, 0.001, 50.,
                      TemperatureUnits.DEG_C, -20., 120.)]
    files = ConfigFiles(tmp_path)

    files.save('all', Configuration().with_channels('Dev1', channels))

    assert files.load('all').channels('Dev1') == channels


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
    ('termination = "RSE"', 'comment = "typo"', 'cDAQ1Mod3.ai.ai0', "unknown key 'comment'"),
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


def test_a_channel_with_only_its_type_gets_the_defaults_of_the_api(tmp_path):
    (tmp_path / 'config_daqmx.toml').write_text(
        'version = 1\n[modules.Dev1.ai.ai0]\ntype = "voltage"\n')

    assert ConfigFiles(tmp_path).load('').channels('Dev1') == [AIVoltage('Dev1/ai0')]


def test_a_file_of_an_unknown_version_is_refused(tmp_path):
    (tmp_path / 'config_daqmx.toml').write_text('version = 7\n')

    with pytest.raises(ConfigFileError, match="version 7"):
        ConfigFiles(tmp_path).load('')


def test_the_user_guide_describes_every_type_key_and_value_of_the_format():
    import dataclasses
    import enum
    from pymodaq_plugins_daqmx.hardware.national_instruments.config_files import CHANNEL_TYPES, channel_fields
    page = (Path(__file__).parent.parent / 'docs' / 'source' / 'user_guide' / 'config_files.rst').read_text()

    missing = []
    for types in CHANNEL_TYPES.values():
        for name, cls in types.items():
            missing += [f'type {name}'] if f'``{name}``' not in page else []
            for f in channel_fields(cls):
                missing += [f'key {f.name}'] if f'``{f.name}``' not in page else []
                if isinstance(f.type, type) and issubclass(f.type, enum.Enum):
                    missing += [f'value {m.name}' for m in f.type if f'``{m.name}``' not in page]
    assert not missing


def test_the_example_of_the_user_guide_is_a_file_the_loader_accepts(tmp_path):
    shutil.copy(Path(__file__).parent.parent / 'docs' / 'source' / 'examples' / 'config_daqmx_example.toml',
                tmp_path / 'config_daqmx.toml')

    assert ConfigFiles(tmp_path).load('').channels('cDAQ1Mod3')[0] == AIVoltage(
        'cDAQ1Mod3/ai0', terminal_config=TerminalConfiguration.RSE)
