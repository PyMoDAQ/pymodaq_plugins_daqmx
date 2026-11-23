"""Generic viewer of the digital input lines of any NI device, as 1D traces.

It is the generic analog viewer with lines in place of channels: the same settings for each module (frequency,
clock, start trigger) and one clocked digital task for each module. A line is 0 or 1, so the data are traces and
never a mean (there is no 0D display). There is no live mode and no configuration file in this version.
"""
from copy import deepcopy

import numpy as np
from pymodaq.control_modules.viewer_utility_classes import main

from pymodaq_plugins_daqmx.daq_viewer_plugins.plugins_0D.daq_0Dviewer_NIDAQmx import DAQ_0DViewer_NIDAQmx
from pymodaq_plugins_daqmx.hardware.national_instruments.api import ChannelKind, DigitalTask


def _digital_params() -> list:
    params = []
    for param in deepcopy(DAQ_0DViewer_NIDAQmx.params):
        if param['name'] == 'config':  # the files describe analog inputs
            continue
        if param['name'] == 'display':  # traces only
            param.update(limits=['1D'], value='1D', visible=False)
        if param['name'] == 'channels':
            param.update(title='Lines:', kind=ChannelKind.DI.value)
        params.append(param)
    return params


class DAQ_1DViewer_NIDAQmx_DI(DAQ_0DViewer_NIDAQmx):
    """Digital input lines (``Dev1/port0/line0``) of any NI device, as 1D traces, one data for each module."""
    params = _digital_params()
    data_name = 'NI DI'
    kind = ChannelKind.DI
    trigger_types = ['none', 'digital edge']  # there is no analog start trigger on a digital input
    has_configuration = False
    live_mode_available = False
    task_class = DigitalTask

    def read_block(self, task) -> np.ndarray:
        """The levels of the lines as floats (0. or 1.), shaped (lines, Nsamples)."""
        return task.read_digital(self.task_samples()).astype(float)


if __name__ == '__main__':
    main(__file__, init=False)
