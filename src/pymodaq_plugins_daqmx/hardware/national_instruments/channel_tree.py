"""The channels of a settings tree: one group for each channel, holding only the parameters of its type.

The types of channels, and the parameters of each, come from the same registry as the configuration files
(``config_files.CHANNEL_TYPES``), which is built from the channel classes of the API.
"""
import enum
from typing import List

from pymodaq_plugins_daqmx.hardware.national_instruments.api import ChannelKind
from pymodaq_plugins_daqmx.hardware.national_instruments.config_files import (CHANNEL_TYPES, channel_fields,
                                                                                 type_name)


def _is_enum(field) -> bool:
    return isinstance(field.type, type) and issubclass(field.type, enum.Enum)


_TEMPERATURE_SUFFIXES = {'DEG_C': '°C', 'DEG_F': '°F', 'K': 'K', 'DEG_R': '°R'}
_RANGE = ('min_val', 'max_val')


def _quantity(type_: str) -> str:
    """What the range of a type of channel measures: a range is meaningful only for that quantity."""
    return {'voltage': 'V', 'current': 'A'}.get(type_, 'temperature')


def _suffix(type_: str, units: str = None) -> str:
    quantity = _quantity(type_)
    return _TEMPERATURE_SUFFIXES.get(units, '') if quantity == 'temperature' else quantity


def _parameter(field, value=None, suffix: str = '') -> dict:
    """The settings parameter of a field of a channel, valued by ``value`` or the default of the field."""
    if value is None:
        value = field.default
    if _is_enum(field):
        return {'title': field.name, 'name': field.name, 'type': 'list',
                'limits': [member.name for member in field.type], 'value': value.name}
    parameter = {'title': field.name, 'name': field.name, 'type': 'float', 'value': float(value)}
    if field.name in _RANGE and suffix:
        parameter['suffix'] = suffix
    return parameter


def _children(kind: ChannelKind, type_: str, channel=None, previous: dict = None, read: bool = True) -> List[dict]:
    types = CHANNEL_TYPES[kind]
    children = [{'title': 'type', 'name': 'type', 'type': 'list', 'limits': list(types), 'value': type_},
                {'title': 'read', 'name': 'read', 'type': 'bool', 'value': read}]  # in the data, or only in the task
    fields = channel_fields(types[type_])
    units = next((getattr(channel, f.name).name if channel is not None else
                  (previous or {}).get(f.name) for f in fields if f.name == 'units'), None)
    if units is None:  # a temperature channel that is new has the default units of its class
        units = next((f.default.name for f in fields if f.name == 'units'), None)
    for field in fields:
        value = getattr(channel, field.name) if channel is not None else (previous or {}).get(field.name)
        children.append(_parameter(field, value, _suffix(type_, units)))
    return children


def update_suffixes(group) -> None:
    """Put the unit of the range (the temperature units can be changed) on the range of the channel of ``group``."""
    suffix = _suffix(group.child('type').value(), group.child('units').value() if group.names.get('units') else None)
    for name in _RANGE:
        group.child(name).setOpts(suffix=suffix)


def channel_params(kind: ChannelKind, channel, read: bool = True) -> dict:
    """The settings group (as a dictionary for ``Parameter.create``) of a channel of the API.

    The title of the group is the name of the channel (``Dev1/ai0``); the name of the parameter has no ``/``.
    """
    return {'title': channel.name, 'name': channel.name.replace('/', '_'), 'type': 'group',
            'children': _children(kind, type_name(channel), channel, read=read), 'removable': True, 'renamable': False}


def is_read(group) -> bool:
    """Whether the samples of the channel that the group describes are in the data (else it is only in the task)."""
    return bool(group.child('read').value())


def channel_from_params(kind: ChannelKind, group):
    """The channel of the API that a settings group describes; a value that makes no sense is a ``ValueError``
    naming the channel."""
    cls = CHANNEL_TYPES[kind][group.child('type').value()]
    values = {}
    for field in channel_fields(cls):
        value = group.child(field.name).value()
        values[field.name] = field.type[value] if _is_enum(field) else value
    try:
        return cls(group.opts['title'], **values)
    except ValueError as error:
        raise ValueError(f"{group.opts['title']}: {error}") from error


def set_type(kind: ChannelKind, group, type_: str) -> None:
    """Give the group the parameters of another type of channel; the values of the parameters the two types share
    are kept."""
    kept = {child.name(): child.value() for child in group.children() if child.name() != 'type'}
    read = kept.pop('read', True)
    if _quantity(type_) != _quantity(group.child('type').value()):  # a range in volts means nothing in amperes
        for name in _RANGE:
            kept.pop(name, None)
    for child in list(group.children()):
        group.removeChild(child)
    previous = {}
    for field in channel_fields(CHANNEL_TYPES[kind][type_]):
        if field.name not in kept:
            continue
        if _is_enum(field):
            if kept[field.name] in field.type.__members__:
                previous[field.name] = field.type[kept[field.name]]
        else:
            previous[field.name] = kept[field.name]
    for spec in _children(kind, type_, None, previous, read):
        group.addChild(spec)
