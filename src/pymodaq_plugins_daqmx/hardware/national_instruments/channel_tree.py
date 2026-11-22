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


def _parameter(field, value=None) -> dict:
    """The settings parameter of a field of a channel, valued by ``value`` or the default of the field."""
    if value is None:
        value = field.default
    if _is_enum(field):
        return {'title': field.name, 'name': field.name, 'type': 'list',
                'limits': [member.name for member in field.type], 'value': value.name}
    return {'title': field.name, 'name': field.name, 'type': 'float', 'value': float(value)}


def _children(kind: ChannelKind, type_: str, channel=None, previous: dict = None) -> List[dict]:
    types = CHANNEL_TYPES[kind]
    children = [{'title': 'type', 'name': 'type', 'type': 'list', 'limits': list(types), 'value': type_}]
    for field in channel_fields(types[type_]):
        value = getattr(channel, field.name) if channel is not None else (previous or {}).get(field.name)
        children.append(_parameter(field, value))
    return children


def channel_params(kind: ChannelKind, channel) -> dict:
    """The settings group (as a dictionary for ``Parameter.create``) of a channel of the API.

    The title of the group is the name of the channel (``Dev1/ai0``); the name of the parameter has no ``/``.
    """
    return {'title': channel.name, 'name': channel.name.replace('/', '_'), 'type': 'group',
            'children': _children(kind, type_name(channel), channel), 'removable': True, 'renamable': False}


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
    for spec in _children(kind, type_, None, previous):
        group.addChild(spec)
