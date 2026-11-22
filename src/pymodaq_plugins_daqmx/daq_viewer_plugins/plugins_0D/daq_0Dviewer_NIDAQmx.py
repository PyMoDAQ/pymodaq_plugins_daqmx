from typing import List

from pymodaq.control_modules.viewer_utility_classes import main
from pyqtgraph.parametertree import Parameter

from pymodaq_plugins_daqmx.hardware.national_instruments.NIDAQmx_AI import DAQ_Viewer_AIBase
from pymodaq_plugins_daqmx.hardware.national_instruments.api import ChannelKind, NIDAQSystem
from pymodaq_plugins_daqmx.hardware.national_instruments.channel_group import channels_of
from pymodaq_plugins_daqmx.hardware.national_instruments.channel_tree import set_type


class DAQ_0DViewer_NIDAQmx(DAQ_Viewer_AIBase):
    """Analog inputs of any NI device, as 0D (mean value) or 1D (trace) data.

    The channels are added to the `channels` group of the settings, each with the parameters of its type of channel.
    """
    params = DAQ_Viewer_AIBase.params + [
        {'title': 'Channels:', 'name': 'channels', 'type': 'ni_channels', 'kind': ChannelKind.AI.value,
         'limits': [], 'children': []},
    ]
    data_name = 'NI AI'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings.child('channels').setLimits(NIDAQSystem().all_channels(ChannelKind.AI))

    def channels(self) -> list:
        return channels_of(self.settings.child('channels'))

    def commit_settings(self, param: Parameter) -> None:
        if param.name() == 'type' and param.parent() is not None:
            set_type(ChannelKind.AI, param.parent(), param.value())
        super().commit_settings(param)


if __name__ == '__main__':
    main(__file__, init=False)
