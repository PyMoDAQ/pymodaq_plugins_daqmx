from copy import deepcopy

from pymodaq.control_modules.viewer_utility_classes import main
from pymodaq_plugins_daqmx.daq_viewer_plugins.plugins_0D.daq_0Dviewer_DAQmxAI import DAQ_0DViewer_DAQmxAI


class DAQ_1DViewer_DAQmxAI(DAQ_0DViewer_DAQmxAI):
    """The 0D viewer of the same name, listed with the 1D viewers: it starts with the 1D (trace) display."""
    params = deepcopy(DAQ_0DViewer_DAQmxAI.params)
    for _param in params:
        if _param['name'] == 'display':
            _param['value'] = '1D'


if __name__ == '__main__':
    main(__file__, init=False)
