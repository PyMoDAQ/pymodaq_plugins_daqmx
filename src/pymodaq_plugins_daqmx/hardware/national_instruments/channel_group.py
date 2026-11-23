"""The extensible group of the channels of a settings tree.

The group has an *Add* button that offers the channels of ``limits`` that are not in it yet. Each channel is a group
of ``channel_tree``: one type of channel at a time, with only the parameters of that type. Import this module for the
parameter type ``ni_channels`` to be known.
"""
from typing import List

from pymodaq_gui.parameter.pymodaq_ptypes import GroupParameter, registerParameterType

from pymodaq_plugins_daqmx.hardware.national_instruments.api import AIVoltage, ChannelKind, NIDAQSystem
from pymodaq_plugins_daqmx.hardware.national_instruments.channel_tree import channel_from_params, channel_params, is_read
from pymodaq_plugins_daqmx.hardware.national_instruments.config_files import CHANNEL_TYPES


class ChannelGroup(GroupParameter):
    """Group holding one channel group for each channel of a kind (``kind='ai'``), chosen among ``limits``.

    A channel is added with the type of channel that comes first for its kind, the user changes it afterwards.
    """

    def __init__(self, **opts):
        opts['type'] = 'ni_channels'
        opts.setdefault('kind', ChannelKind.AI.value)
        opts.setdefault('limits', [])
        opts['available'] = list(opts['limits'])
        opts['addText'] = 'Add'
        opts['addList'] = list(opts['available'])
        super().__init__(**opts)
        self.sigChildAdded.connect(self._update_add_list)
        self.sigChildRemoved.connect(self._update_add_list)

    @property
    def kind(self) -> ChannelKind:
        return ChannelKind(self.opts['kind'])

    def _used(self) -> List[str]:
        return [child.opts['title'] for child in self.children()]

    def _update_add_list(self, *args) -> None:
        used = self._used()
        self.setOpts(addList=[name for name in self.opts['available'] if name not in used])

    def setOpts(self, **opts) -> None:
        super().setOpts(**opts)
        if 'available' in opts:  # also what the GUI receives from the plugin: it then follows the children by itself
            self._update_add_list()

    def setLimits(self, limits) -> None:
        """The channels that can be added, sent to the GUI as the option ``available``: the group of the GUI
        keeps its own add list up to date when it adds or removes a channel, the plugin cannot do it for it."""
        self.setOpts(available=list(limits))

    def setChannels(self, channels, unread=()) -> None:
        """Replace the channels of the group by these channels of the API, in this order; the ones named in
        ``unread`` are not read (they are in the task but not in the data)."""
        for child in list(self.children()):
            self.removeChild(child)
        for channel in channels:
            self.addChild(channel_params(self.kind, channel, read=channel.name not in unread))

    def addNew(self, typ=None) -> None:
        """Add the channel named ``typ`` (``Dev1/ai0``), unless it is already in the group."""
        if typ is None or typ in self._used():
            return
        self.addChild(channel_params(self.kind, self._default_channel(typ)))

    def _default_channel(self, name: str):
        """The channel to add, of the first type that its device can measure (a module may only measure a
        temperature: the driver refuses another type), with the values of that type; a voltage input gets the widest
        range of the device, as a module may not accept the usual +-10 V."""
        types = CHANNEL_TYPES[self.kind]
        device = name.split('/')[0]
        measures, ranges = [], []
        if self.kind is ChannelKind.AI:
            try:
                measures = NIDAQSystem().ai_measurement_types(device)
                ranges = NIDAQSystem().ai_voltage_ranges(device)
            except ValueError:  # not a device of the system
                pass
        channel_type = next((cls for label, cls in types.items() if _MEASURES.get(label) in measures),
                            next(iter(types.values())))
        if channel_type is AIVoltage and ranges:
            low, high = max(ranges, key=lambda pair: pair[1] - pair[0])
            return AIVoltage(name, min_val=low, max_val=high)
        return channel_type(name)


_MEASURES = {'voltage': 'voltage', 'current': 'current', 'thermocouple': 'temperature_thermocouple',
             'rtd': 'temperature_rtd'}  # the type of channel -> what the device reports it can measure


registerParameterType('ni_channels', ChannelGroup, override=True)


def unread_of(group) -> List[str]:
    """The names of the channels of the group that are not read, in its order."""
    return [child.opts['title'] for child in group.children() if not is_read(child)]


def channels_of(group) -> list:
    """The channels of the API that the group describes, in its order; a mistake in one is a ``ValueError`` that
    names it."""
    return [channel_from_params(ChannelKind(group.opts['kind']), child) for child in group.children()]
