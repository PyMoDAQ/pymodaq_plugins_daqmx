"""Generic actuator for one output of an NI device: an analog output (a level in volts or amperes) or a digital line
(0 or 1, or a pulse to trigger something).

The output is driven on demand, one point at a time: there is no clock and no waveform. For ramps, see
``DAQ_Move_NIDAQmx_RampOutput``. The level of an output cannot be read back, so the position is the last level
written. The output goes to 0 V (or low) when the plugin starts, when its channel changes and when it closes.
"""
import time
from typing import Union

import numpy as np
from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, DataActuator, DataActuatorType,
                                                          comon_parameters_fun, main)
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.logger import get_module_name, set_logger

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AnalogOutputTask, AOCurrent, AOVoltage, ChannelKind, DigitalOut, DigitalTask, NIDAQSystem, TaskConfig)

logger = set_logger(get_module_name(__file__))

ANALOG_TYPES = {'voltage': (AOVoltage, 'V'), 'current': (AOCurrent, 'A')}  # type -> channel of the API, unit
ANALOG_ONLY = ('type', 'min_val', 'max_val')  # the settings that only an analog output has
DIGITAL_ONLY = ('pulse', 'pulse_width')  # the settings that only a digital line has


def is_digital(channel: str) -> bool:
    """Whether ``channel`` is a digital line (``Dev1/port0/line3``) and not an analog output (``Dev1/ao0``)."""
    return '/port' in channel


class DAQ_Move_NIDAQmx(DAQ_Move_base):
    """One output of an NI device, driven one point at a time. Analog: the level in V or A, cut to the range of the
    output. Digital: 0 or 1; with ``pulse``, a move to 1 gives a pulse of ``pulse_width`` ms and the line falls back
    to 0."""
    _controller_units = 'V'
    is_multiaxes = False
    _axis_names = ['output']
    _epsilons = [1e-3]
    data_actuator_type = DataActuatorType.DataActuator
    params = [
        {'title': 'Output:', 'name': 'channel', 'type': 'list', 'limits': [],
         'tip': 'An analog output (Dev1/ao0) or a digital line (Dev1/port0/line0)'},
        {'title': 'Type:', 'name': 'type', 'type': 'list', 'limits': list(ANALOG_TYPES), 'value': 'voltage'},
        {'title': 'Min:', 'name': 'min_val', 'type': 'float', 'value': -10., 'suffix': 'V',
         'tip': 'Lowest level of the output; the level asked is cut to the range'},
        {'title': 'Max:', 'name': 'max_val', 'type': 'float', 'value': 10., 'suffix': 'V'},
        {'title': 'Pulse:', 'name': 'pulse', 'type': 'bool', 'value': False, 'visible': False,
         'tip': 'A move to 1 sets the line high for the pulse width, then low again (to trigger something)'},
        {'title': 'Pulse width (ms):', 'name': 'pulse_width', 'type': 'float', 'value': 10., 'min': 0.,
         'visible': False},
    ] + comon_parameters_fun(is_multiaxes, axis_names=_axis_names, epsilon=_epsilons)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        system = NIDAQSystem()
        outputs = system.all_channels(ChannelKind.AO) + system.all_channels(ChannelKind.DO)
        self.settings.child('channel').setLimits(outputs)
        self.show_settings()

    def ini_attributes(self):
        self.controller = None  # the task of the output
        self.level = 0.  # the last level written

    # --- the output ---------------------------------------------------------------------------------------------

    def show_settings(self) -> None:
        """Only the settings of the kind of output that is chosen are visible, and the unit follows."""
        digital = is_digital(self.settings['channel'] or '')
        for name in ANALOG_ONLY:
            self.settings.child(name).setOpts(visible=not digital)
        for name in DIGITAL_ONLY:
            self.settings.child(name).setOpts(visible=digital)
        unit = '' if digital else ANALOG_TYPES[self.settings['type']][1]
        for name in ('min_val', 'max_val'):
            self.settings.child(name).setOpts(suffix=unit)
        self.axis_unit = unit

    def open_output(self) -> None:
        """Make the task of the chosen output and set the output to 0."""
        name = self.settings['channel']
        if is_digital(name):
            self.controller = DigitalTask(TaskConfig(channels=[DigitalOut(name)]))
        else:
            cls = ANALOG_TYPES[self.settings['type']][0]
            self.controller = AnalogOutputTask(TaskConfig(channels=[cls(name, self.settings['min_val'],
                                                                        self.settings['max_val'])]))
        self.write(0.)

    def close_output(self) -> None:
        """Set the output to 0 and release it: it is the one of its channel only while the task is open."""
        if self.controller is None:
            return
        try:
            self.write(0.)
        except Exception:  # closing must go on: the channel has to be released
            logger.warning('The output could not be set to 0', exc_info=True)
        self.controller.close()
        self.controller = None

    def write(self, level: float) -> None:
        """Drive the output to ``level`` now (a digital line is high from 0.5 on)."""
        if is_digital(self.settings['channel']):
            self.controller.write_digital(bool(level >= 0.5))
            self.level = float(level >= 0.5)
        else:
            self.controller.write_analog(float(level))
            self.level = float(level)

    def clip(self, level: float) -> float:
        """The level inside the range of an analog output (a message tells it was cut)."""
        if is_digital(self.settings['channel']):
            return level
        clipped = float(np.clip(level, self.settings['min_val'], self.settings['max_val']))
        if clipped != level:
            self.emit_status(ThreadCommand('outofbounds'))
        return clipped

    # --- the actuator -------------------------------------------------------------------------------------------

    def ini_stage(self, controller=None):
        self.show_settings()  # the settings may have been given before the initialization
        self.open_output()
        return 'NI output ready', True

    def close(self):
        self.close_output()

    def commit_settings(self, param):
        if param.name() in ('channel', 'type', 'min_val', 'max_val') and self.controller is not None:
            self.close_output()  # the old output goes to 0 before the new one is driven
            self.show_settings()
            self.open_output()
        elif param.name() in ('channel', 'type'):
            self.show_settings()

    def get_actuator_value(self) -> DataActuator:
        return DataActuator(data=self.level, units=self.axis_unit)

    def move_abs(self, value: DataActuator):
        value = self.check_bound(value)
        level = self.clip(float(value.value(self.axis_unit)))
        self.target_value = DataActuator(data=level, units=self.axis_unit)
        if is_digital(self.settings['channel']) and self.settings['pulse'] and level >= 0.5:
            self.write(1.)
            time.sleep(self.settings['pulse_width'] * 1e-3)
            self.write(0.)
            self.target_value = DataActuator(data=0., units=self.axis_unit)  # the line is low again
        else:
            self.write(level)

    def move_rel(self, value: DataActuator):
        self.move_abs(DataActuator(data=self.level + float(value.value(self.axis_unit)), units=self.axis_unit))

    def move_home(self):
        self.move_abs(DataActuator(data=0., units=self.axis_unit))

    def stop_motion(self):
        pass  # a level is written at once: there is nothing to stop


if __name__ == '__main__':
    main(__file__)
