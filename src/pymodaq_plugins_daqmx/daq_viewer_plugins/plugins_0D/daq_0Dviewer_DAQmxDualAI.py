from pymodaq.control_modules.viewer_utility_classes import main
from pymodaq_plugins_daqmx.hardware.national_instruments.NIDAQmx_AI import (
    DAQ_Viewer_AIBase, AI_CHANNELS, default_channel)


class DAQ_0DViewer_DAQmxDualAI(DAQ_Viewer_AIBase):
    """Two analog inputs of a NI device acquired together, as 0D (mean value) or 1D (trace) data."""
    params = DAQ_Viewer_AIBase.params + [
        {'title': 'AI0:', 'name': 'ai_channel0', 'type': 'list', 'limits': AI_CHANNELS,
         'value': default_channel(2)},
        {'title': 'AI1:', 'name': 'ai_channel1', 'type': 'list', 'limits': AI_CHANNELS,
         'value': default_channel(3)},
    ]
    data_name = 'NI DualAI'

    def channel_names(self):
        return [self.settings['ai_channel0'], self.settings['ai_channel1']]


if __name__ == '__main__':
    main(__file__)
