import numpy as np

from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, comon_parameters_fun, DataActuatorType,
                                                          DataActuator, main)
from pymodaq.utils.logger import set_logger, get_module_name

from pymodaq_plugins_daqmx.hardware.national_instruments.daqmxni import NIDAQmx, ChannelType
from pymodaq_plugins_daqmx.hardware.national_instruments.ramp_output import RampOutputController

logger = set_logger(get_module_name(__file__))

AO_CHANNELS = NIDAQmx.get_NIDAQ_channels(source_type=ChannelType.ANALOG_OUTPUT)
COUNTER_CHANNELS = NIDAQmx.get_NIDAQ_channels(source_type=ChannelType.COUNTER_OUTPUT)


class DAQ_Move_NIDAQmx_RampOutput(DAQ_Move_base):
    """A quantity driven by an analog output of a NI device, changed by voltage ramps.

    The value is the output voltage times a conversion factor (nm/V). A move is a succession of steps of
    `step_size` taking each `step_time`, timed by a counter used as a clock. Several outputs (axes x, y, z) can be
    moved with one clock: the first axis created is the master and owns the clock, give to the others the same
    controller ID.
    """
    _controller_units = 'nm'
    is_multiaxes = True
    _axis_names = ['x', 'y', 'z']
    _epsilons = [10., 10., 10.]
    data_actuator_type = DataActuatorType.DataActuator
    params = [
        {'title': 'Output channel:', 'name': 'analog_channel', 'type': 'list', 'limits': AO_CHANNELS,
         'value': AO_CHANNELS[0] if AO_CHANNELS else ''},
        {'title': 'Clock channel:', 'name': 'clock_channel', 'type': 'list', 'limits': COUNTER_CHANNELS,
         'value': COUNTER_CHANNELS[0] if COUNTER_CHANNELS else ''},
        {'title': 'Step size (nm)', 'name': 'step_size', 'type': 'float', 'value': 100.0, 'min': 1e-6},
        {'title': 'Step time (ms)', 'name': 'step_time', 'type': 'float', 'value': 10.0, 'min': 1e-3},
        {'title': 'Conversion factor (nm/V)', 'name': 'conv_factor', 'type': 'float', 'value': 7500.0},
    ] + comon_parameters_fun(is_multiaxes, axis_names=_axis_names, epsilon=_epsilons)

    def ini_attributes(self):
        self.controller: RampOutputController = None

    @property
    def axis(self) -> str:
        return self.axis_name

    def configure_axis(self):
        """Declare the output of this axis, over the whole range of the device: the bounds are the user's."""
        self.controller.configure_axis(self.axis, self.settings['analog_channel'], -10., 10.)

    def ini_stage(self, controller=None):
        if self.is_master:
            self.controller = RampOutputController()
            self.controller.clock_channel = self.settings['clock_channel']
        else:
            self.controller = controller
        self.configure_axis()
        self.controller.ramp(self.axis, [0.], self.settings['step_time'] * 1e-3)  # the output cannot be read back
        return 'NI analog output ramp ready', True

    def close(self):
        if self.is_master and self.controller is not None:
            self.controller.close()

    def commit_settings(self, param):
        if param.name() == 'analog_channel':
            self.controller.stop()
            self.configure_axis()
        elif param.name() == 'clock_channel' and self.is_master:
            self.controller.stop()
            self.controller.clock_channel = param.value()

    def get_actuator_value(self) -> DataActuator:
        position = DataActuator(data=self.controller.voltage(self.axis) * self.settings['conv_factor'],
                                units=self.axis_unit)
        return self.get_position_with_scaling(position)

    def _ramp_to(self, target: float):
        """Ramp the output from where it is to `target` (in controller units)."""
        conv = self.settings['conv_factor']
        start = self.controller.voltage(self.axis) * conv
        step = self.settings['step_size']
        if abs(target - start) <= step:
            positions = np.array([target])
        else:
            positions = np.linspace(start, target, int(np.ceil(abs(target - start) / step)) + 1)[1:]
        self.controller.ramp(self.axis, positions / conv, self.settings['step_time'] * 1e-3)

    def move_abs(self, value: DataActuator):
        value = self.check_bound(value)
        self.target_value = value
        value = self.set_position_with_scaling(value)
        self._ramp_to(value.value(self.axis_unit))

    def move_rel(self, value: DataActuator):
        value = self.check_bound(self.current_value + value) - self.current_value
        self.target_value = value + self.current_value
        value = self.set_position_with_scaling(self.target_value)
        self._ramp_to(value.value(self.axis_unit))

    def move_home(self):
        self.move_abs(DataActuator(data=0., units=self.axis_unit))

    def stop_motion(self):
        self.controller.stop()


if __name__ == '__main__':
    main(__file__)
