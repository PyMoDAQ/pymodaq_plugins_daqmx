from pymodaq.control_modules.viewer_utility_classes import main
from pymodaq_plugins_daqmx.hardware.national_instruments.NIDAQmx_AI import (
    DAQ_Viewer_AIBase, AI_CHANNELS, default_channel)


class DAQ_0DViewer_DAQmxAI(DAQ_Viewer_AIBase):
    """Analog input of a NI device as 0D (mean value) or 1D (trace) data."""
    params = DAQ_Viewer_AIBase.params + [
        {'title': 'AI:', 'name': 'ai_channel', 'type': 'list', 'limits': AI_CHANNELS,
         'value': default_channel(0)},
    ]
    data_name = 'NI AI'

    def channel_names(self):
        return [self.settings['ai_channel']]


if __name__ == '__main__':
    main(__file__)
