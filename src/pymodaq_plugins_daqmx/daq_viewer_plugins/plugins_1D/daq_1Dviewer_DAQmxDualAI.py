from copy import deepcopy

from pymodaq.control_modules.viewer_utility_classes import main
from pymodaq_plugins_daqmx.daq_viewer_plugins.plugins_0D.daq_0Dviewer_DAQmxDualAI import DAQ_0DViewer_DAQmxDualAI


class DAQ_1DViewer_DAQmxDualAI(DAQ_0DViewer_DAQmxDualAI):
    """The 0D viewer of the same name, listed with the 1D viewers: it starts with the 1D (trace) display."""
    params = deepcopy(DAQ_0DViewer_DAQmxDualAI.params)
    for _param in params:
        if _param['name'] == 'display':
            _param['value'] = '1D'


if __name__ == '__main__':
    main(__file__, init=False)
