"""Configuration files describing the channels of the modules of a bench, as ``config_daqmx[_<suffix>].toml``.

The files live in one folder (the ``daqmx`` folder of the PyMoDAQ system configuration folder, so that every user of
the computer sees them), and a configuration is named by its *suffix* only: ``''`` is the historical
``config_daqmx.toml``. The layout of the files is the one of the previous versions of the plugin.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import toml
from nidaqmx.constants import TerminalConfiguration, ThermocoupleType

from pymodaq_plugins_daqmx.hardware.national_instruments.api import AIThermocouple, AIVoltage


def system_folder() -> Path:
    """The folder of the configuration files shared by all the users of the computer."""
    from pymodaq_utils.config import get_set_config_dir
    return get_set_config_dir('daqmx', user=False)


@dataclass
class _Module:
    name: str
    product: str = ''
    channels: list = field(default_factory=list)
    notes: Dict[str, str] = field(default_factory=dict)   # channel name -> free text of the file


@dataclass
class _Device:
    name: str
    product: str = ''
    modules: List[_Module] = field(default_factory=list)


class Configuration:
    """The devices, modules and channels of a bench; the channels are objects of the API."""

    def __init__(self, devices: Optional[List[_Device]] = None):
        self._devices = devices or []

    def channels(self, module: str) -> list:
        return [channel for device in self._devices for mod in device.modules if mod.name == module
                for channel in mod.channels]


class ConfigFileError(ValueError):
    """A configuration file that cannot be used; the message tells the file and the entry."""


def _required(entry: dict, key: str):
    if key not in entry:
        raise ValueError(f"missing {key!r}")
    return entry[key]


def _member(enum, entry: dict, key: str):
    value = _required(entry, key)
    try:
        return enum[value]
    except KeyError:
        raise ValueError(f"unknown {key} {value!r}, expected one of {[member.name for member in enum]}") from None


def _ai_channel(name: str, entry: dict):
    kind = _required(entry, 'analog_type')
    limits = dict(min_val=float(_required(entry, 'value_min')), max_val=float(_required(entry, 'value_max')))
    if kind == 'VOLTAGE':
        return AIVoltage(name, terminal_config=_member(TerminalConfiguration, entry, 'termination'), **limits)
    if kind == 'TEMPERATURE_THERMOCOUPLE':
        return AIThermocouple(name, thermocouple_type=_member(ThermocoupleType, entry, 'thermo_type'), **limits)
    raise ValueError(f"analog_type {kind!r} is not supported, expected 'VOLTAGE' or 'TEMPERATURE_THERMOCOUPLE'")


def _ai_entry(channel, note: str = '') -> dict:
    entry = {'name': channel.name, 'source': 'ANALOG_INPUT'}
    if isinstance(channel, AIVoltage):
        entry.update(analog_type='VOLTAGE', value_min=channel.min_val, value_max=channel.max_val,
                     termination=channel.terminal_config.name)
    else:
        entry.update(analog_type='TEMPERATURE_THERMOCOUPLE', value_min=channel.min_val, value_max=channel.max_val,
                     thermo_type=channel.thermocouple_type.name)
    entry['info'] = note
    return entry


class ConfigFiles:
    def __init__(self, folder: Optional[Path] = None):
        self.folder = Path(folder) if folder is not None else system_folder()

    def path(self, suffix: str) -> Path:
        return self.folder / (f'config_daqmx_{suffix}.toml' if suffix else 'config_daqmx.toml')

    def suffixes(self) -> List[str]:
        """The suffixes of the configuration files of the folder (``''`` for ``config_daqmx.toml``), sorted."""
        found = []
        for path in self.folder.glob('config_daqmx*.toml'):
            suffix = path.stem[len('config_daqmx'):]
            if suffix == '' or suffix.startswith('_') and len(suffix) > 1:
                found.append(suffix[1:])
        return sorted(found)

    def load(self, suffix: str) -> Configuration:
        try:
            content = toml.loads(self.path(suffix).read_text())
        except toml.TomlDecodeError as error:
            raise ConfigFileError(f'{self.path(suffix)}: not a valid toml file ({error})') from error
        devices = []
        for device_entry in content.get('NIDAQ_Devices', {}).values():
            if not isinstance(device_entry, dict):
                continue
            device = _Device(device_entry['name'], device_entry.get('product', ''))
            for module_entry in device_entry.values():
                if not isinstance(module_entry, dict):
                    continue
                module = _Module(module_entry['name'], module_entry.get('product', ''))
                for key, entry in module_entry.get('ai', {}).items():
                    try:
                        channel = _ai_channel(f"{module.name}/{key}", entry)
                    except (ValueError, TypeError) as error:
                        raise ConfigFileError(f"{self.path(suffix)}: [{module.name}.ai.{key}] {error}") from error
                    module.channels.append(channel)
                    module.notes[channel.name] = entry.get('info', '')
                device.modules.append(module)
            devices.append(device)
        return Configuration(devices)

    def save(self, suffix: str, configuration: Configuration) -> None:
        content = {'title': 'Configuration file of the DAQmx plugin', 'NIDAQ_Devices': {}}
        for number, device in enumerate(configuration._devices, 1):
            device_entry = content['NIDAQ_Devices'][f'DEVICE{number:02d}'] = {
                'title': 'Configuration entry for a NIDAQmx device', 'name': device.name, 'product': device.product}
            for index, module in enumerate(device.modules, 1):
                module_entry = device_entry[f'MODULE{index:02d}'] = {
                    'title': 'Module plugged in a NIDAQmx device', 'name': module.name, 'product': module.product}
                if module.channels:
                    module_entry['ai'] = {channel.name.split('/')[-1]: _ai_entry(channel, module.notes.get(channel.name, ''))
                                          for channel in module.channels}
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path(suffix).write_text(toml.dumps(content))
