"""The extensible group of the channels of a settings tree.

The group has an *Add* button that offers the channels of ``limits`` that are not in it yet. Each channel is a group
of ``channel_tree``: one type of channel at a time, with only the parameters of that type. Import this module for the
parameter type ``ni_channels`` to be known.
"""
from typing import List

from pymodaq_gui.parameter.pymodaq_ptypes import GroupParameter, registerParameterType

from pymodaq_plugins_daqmx.hardware.national_instruments.api import ChannelKind
from pymodaq_plugins_daqmx.hardware.national_instruments.channel_tree import channel_from_params, channel_params
from pymodaq_plugins_daqmx.hardware.national_instruments.config_files import CHANNEL_TYPES


class ChannelGroup(GroupParameter):
    """Group holding one channel group for each channel of a kind (``kind='ai'``), chosen among ``limits``.

    A channel is added with the type of channel that comes first for its kind, the user changes it afterwards.
    """

    def __init__(self, **opts):
        opts['type'] = 'ni_channels'
        opts.setdefault('kind', ChannelKind.AI.value)
        opts.setdefault('limits', [])
        opts['addText'] = 'Add'
        opts['addList'] = list(opts['limits'])
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
        self.setOpts(addList=[name for name in self.opts['limits'] if name not in used])

    def setLimits(self, limits) -> None:
        """The channels that can be added."""
        self.opts['limits'] = list(limits)
        self._update_add_list()

    def addNew(self, typ=None) -> None:
        """Add the channel named ``typ`` (``Dev1/ai0``), unless it is already in the group."""
        if typ is None or typ in self._used():
            return
        first_type = next(iter(CHANNEL_TYPES[self.kind].values()))
        self.addChild(channel_params(self.kind, first_type(typ)))


registerParameterType('ni_channels', ChannelGroup, override=True)


def channels_of(group) -> list:
    """The channels of the API that the group describes, in its order; a mistake in one is a ``ValueError`` that
    names it."""
    return [channel_from_params(ChannelKind(group.opts['kind']), child) for child in group.children()]
