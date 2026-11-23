"""Generic actuator for one analog output of an NI device: a level in volts or amperes, set on demand.

There is no clock and no waveform (for voltage ramps, see ``DAQ_Move_NIDAQmx_RampOutput``; for a digital line,
``DAQ_Move_NIDAQmx_DO``). The common behaviour (zero at start, change and close, position = last level written) is in
``OutputActuator``.
"""
import numpy as np
from pymodaq.control_modules.daq_move_ui.utils import UiType
from pymodaq.control_modules.move_utility_classes import comon_parameters_fun, main
from pymodaq.utils.daq_utils import ThreadCommand

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (AnalogOutputTask, AOCurrent, AOVoltage,
                                                                      ChannelKind, TaskConfig)
from pymodaq_plugins_daqmx.hardware.national_instruments.output_actuator import OutputActuator

ANALOG_TYPES = {'voltage': (AOVoltage, 'V'), 'current': (AOCurrent, 'A')}  # type -> channel of the API, unit


class DAQ_Move_NIDAQmx(OutputActuator):
    """One analog output: the level in V or A, cut to the range of the output."""
    _controller_units = 'V'
    _epsilons = [1e-3]
    ui_type = UiType.SIMPLE  # a value to type and a button to set it
    output_kind = ChannelKind.AO
    rebuild_on = ('channel', 'type', 'min_val', 'max_val')
    params = [
        {'title': 'Output:', 'name': 'channel', 'type': 'list', 'limits': [], 'tip': 'An analog output (Dev1/ao0)'},
        {'title': 'Type:', 'name': 'type', 'type': 'list', 'limits': list(ANALOG_TYPES), 'value': 'voltage'},
        {'title': 'Min:', 'name': 'min_val', 'type': 'float', 'value': -10., 'suffix': 'V',
         'tip': 'Lowest level of the output; the level asked is cut to the range'},
        {'title': 'Max:', 'name': 'max_val', 'type': 'float', 'value': 10., 'suffix': 'V'},
    ] + comon_parameters_fun(False, axis_names=OutputActuator._axis_names, epsilon=_epsilons)

    def make_task(self):
        cls = ANALOG_TYPES[self.settings['type']][0]
        return AnalogOutputTask(TaskConfig(channels=[cls(self.settings['channel'], self.settings['min_val'],
                                                         self.settings['max_val'])]))

    def send(self, level: float) -> None:
        self.controller.write_analog(float(level))
        self.level = float(level)

    def show_settings(self) -> None:
        unit = ANALOG_TYPES[self.settings['type']][1]
        for name in ('min_val', 'max_val'):
            self.settings.child(name).setOpts(suffix=unit)
        self.axis_unit = unit

    def clip(self, level: float) -> float:
        clipped = float(np.clip(level, self.settings['min_val'], self.settings['max_val']))
        if clipped != level:
            self.emit_status(ThreadCommand('outofbounds'))
        return clipped


if __name__ == '__main__':
    main(__file__)
