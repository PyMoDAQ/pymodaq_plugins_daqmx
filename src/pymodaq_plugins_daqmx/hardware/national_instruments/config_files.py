"""Configuration files describing the channels of the modules of a bench, as ``config_daqmx[_<suffix>].toml``.

The files live in one folder (the ``daqmx`` folder of the PyMoDAQ system configuration folder, so that every user of
the computer sees them), and a configuration is named by its *suffix* only: ``''`` is ``config_daqmx.toml``.
The format is described in the user guide ("Configuration files"). Files of the previous versions of the plugin
(``NIDAQ_Devices`` layout) are read too; saving always writes the current format.
"""
import dataclasses
import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import toml
from nidaqmx.constants import TerminalConfiguration, ThermocoupleType, UsageTypeAI

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AICurrent, AIRtd, AIThermocouple, AIVoltage, ChannelKind)

FORMAT_VERSION = 1

#: channel types of a configuration file, by the ``type`` key, for each kind of channel
CHANNEL_TYPES = {
    ChannelKind.AI: {'voltage': AIVoltage, 'current': AICurrent, 'thermocouple': AIThermocouple, 'rtd': AIRtd},
}


def system_folder() -> Path:
    """The folder of the configuration files shared by all the users of the computer."""
    from pymodaq_utils.config import get_set_config_dir
    return get_set_config_dir('daqmx', user=False)


class ConfigFileError(ValueError):
    """A configuration file that cannot be used; the message tells the file and the entry."""


@dataclass
class _Module:
    product: str = ''
    channels: list = field(default_factory=list)
    notes: Dict[str, str] = field(default_factory=dict)   # channel name -> free text of the file


class Configuration:
    """The devices, modules and channels of a bench; the channels are objects of the API."""

    def __init__(self, description: str = ''):
        self.description = description
        self.devices: Dict[str, str] = {}        # device name -> product
        self.modules: Dict[str, _Module] = {}    # module name -> its content

    def channels(self, module: str) -> list:
        return list(self.modules[module].channels) if module in self.modules else []

    def with_channels(self, module: str, channels: list, product: str = '') -> 'Configuration':
        """A copy where ``module`` has these channels (the notes of the channels that stay are kept)."""
        new = Configuration(self.description)
        new.devices = dict(self.devices)
        new.modules = {name: dataclasses.replace(mod, channels=list(mod.channels), notes=dict(mod.notes))
                       for name, mod in self.modules.items()}
        previous = new.modules.get(module, _Module(product))
        kept = {channel.name: previous.notes.get(channel.name, '') for channel in channels}
        new.modules[module] = _Module(product or previous.product, list(channels), kept)
        return new


def _type_name(channel) -> str:
    for kind, types in CHANNEL_TYPES.items():
        for name, cls in types.items():
            if type(channel) is cls:
                return name
    raise ValueError(f'cannot save a channel of type {type(channel).__name__}')


def _channel_fields(cls):
    return [f for f in dataclasses.fields(cls) if f.name != 'name']


def _decode(cls, name: str, entry: dict, shown=None):
    """A channel of class ``cls`` from the entry of a file; a mistake is a ``ValueError`` naming the key.

    ``shown`` gives the name a key has in the file, when it is not the one of the API (previous format).
    """
    shown = shown or {}
    known = {f.name: f for f in _channel_fields(cls)}
    unknown = sorted(set(entry) - set(known) - {'type', 'info'})
    if unknown:
        raise ValueError(f"unknown key {unknown[0]!r}, expected {sorted(known) + ['info']}")
    values = {}
    for key, value in entry.items():
        if key in ('type', 'info'):
            continue
        annotation = known[key].type
        if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
            try:
                values[key] = annotation[value]
            except KeyError:
                raise ValueError(f"unknown {shown.get(key, key)} {value!r}, "
                                 f"expected one of {[m.name for m in annotation]}") from None
        else:
            values[key] = float(value)
    missing = [f.name for f in _channel_fields(cls) if f.default is dataclasses.MISSING and f.name not in values]
    if missing:
        raise ValueError(f"missing {shown.get(missing[0], missing[0])!r}")
    return cls(name, **values)


def _encode(channel, note: str) -> dict:
    entry = {'type': _type_name(channel)}
    for f in _channel_fields(type(channel)):
        value = getattr(channel, f.name)
        entry[f.name] = value.name if isinstance(value, enum.Enum) else float(value)
    entry['info'] = note
    return entry


# keys of the previous format, by type, and the key of the current format they became
_PREVIOUS_KEYS = {'value_min': 'min_val', 'value_max': 'max_val', 'termination': 'terminal_config',
                  'thermo_type': 'thermocouple_type'}
_PREVIOUS_NAMES = {new: old for old, new in _PREVIOUS_KEYS.items()}
_PREVIOUS_TYPES = {UsageTypeAI.VOLTAGE: 'voltage', UsageTypeAI.CURRENT: 'current',
                   UsageTypeAI.TEMPERATURE_THERMOCOUPLE: 'thermocouple'}


def _from_previous(entry: dict) -> dict:
    """The entry of a file of the previous format, as an entry of the current one."""
    if 'analog_type' not in entry:
        raise ValueError("missing 'analog_type'")
    try:
        kind = UsageTypeAI[entry['analog_type']]
    except KeyError:
        raise ValueError(f"unknown analog_type {entry['analog_type']!r}, expected one of "
                         f"{[m.name for m in UsageTypeAI]}") from None
    if kind not in _PREVIOUS_TYPES:
        raise ValueError(f"analog_type {kind.name!r} is not supported in this format, "
                         f"expected one of {[k.name for k in _PREVIOUS_TYPES]}")
    new = {'type': _PREVIOUS_TYPES[kind]}
    for key, value in entry.items():
        if key in ('name', 'source', 'analog_type'):
            continue
        new[_PREVIOUS_KEYS.get(key, key)] = value
    return new


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
        path = self.path(suffix)
        try:
            content = toml.loads(path.read_text())
        except toml.TomlDecodeError as error:
            raise ConfigFileError(f'{path}: not a valid toml file ({error})') from error
        if 'NIDAQ_Devices' in content:
            return self._load_previous(path, content)
        version = content.get('version')
        if version != FORMAT_VERSION:
            raise ConfigFileError(f'{path}: version {version!r} is not supported, expected {FORMAT_VERSION}')
        configuration = Configuration(content.get('description', ''))
        for name, entry in content.get('devices', {}).items():
            configuration.devices[name] = entry.get('product', '')
        for name, entry in content.get('modules', {}).items():
            module = configuration.modules[name] = _Module(entry.get('product', ''))
            for kind in ChannelKind:
                for key, channel_entry in entry.get(kind.value, {}).items():
                    self._add(path, module, name, kind, key, channel_entry)
        return configuration

    def _add(self, path, module, module_name, kind, key, entry, shown=None):
        where = f'[{module_name}.{kind.value}.{key}]'
        try:
            types = CHANNEL_TYPES.get(kind, {})
            if 'type' not in entry:
                raise ValueError("missing 'type'")
            if entry['type'] not in types:
                raise ValueError(f"unknown type {entry['type']!r}, expected one of {sorted(types)}")
            channel = _decode(types[entry['type']], f'{module_name}/{key}', entry, shown)
        except (ValueError, TypeError) as error:
            raise ConfigFileError(f'{path}: {where} {error}') from error
        module.channels.append(channel)
        module.notes[channel.name] = entry.get('info', '')

    def _load_previous(self, path, content) -> Configuration:
        configuration = Configuration(content.get('title', ''))
        for device_entry in content['NIDAQ_Devices'].values():
            if not isinstance(device_entry, dict):
                continue
            configuration.devices[device_entry['name']] = device_entry.get('product', '')
            for module_entry in device_entry.values():
                if not isinstance(module_entry, dict):
                    continue
                name = module_entry['name']
                module = configuration.modules[name] = _Module(module_entry.get('product', ''))
                for key, entry in module_entry.get(ChannelKind.AI, {}).items():
                    try:
                        converted = _from_previous(entry)
                    except ValueError as error:
                        raise ConfigFileError(f'{path}: [{name}.ai.{key}] {error}') from error
                    self._add(path, module, name, ChannelKind.AI, key, converted, _PREVIOUS_NAMES)
        return configuration

    def save(self, suffix: str, configuration: Configuration) -> None:
        content = {'version': FORMAT_VERSION, 'description': configuration.description}
        if configuration.devices:
            content['devices'] = {name: {'product': product} for name, product in configuration.devices.items()}
        content['modules'] = {}
        for name, module in configuration.modules.items():
            entry = content['modules'][name] = {'product': module.product}
            if module.channels:
                entry[ChannelKind.AI.value] = {channel.name.split('/')[-1]: _encode(channel, module.notes.get(channel.name, ''))
                                               for channel in module.channels}
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path(suffix).write_text(toml.dumps(content))

