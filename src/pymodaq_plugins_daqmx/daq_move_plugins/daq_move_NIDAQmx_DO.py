"""Generic actuator for one digital output line of an NI device: 0 (low) or 1 (high), or a pulse.

The common behaviour (zero at start, change and close, position = last level written) is in ``OutputActuator``.
"""
import time

from pymodaq.control_modules.daq_move_ui.utils import UiType
from pymodaq.control_modules.move_utility_classes import DataActuator, comon_parameters_fun, main
from pymodaq.utils.daq_utils import ThreadCommand

from pymodaq_plugins_daqmx.hardware.national_instruments.api import ChannelKind, DigitalOut, DigitalTask, TaskConfig
from pymodaq_plugins_daqmx.hardware.national_instruments.output_actuator import OutputActuator


class DAQ_Move_NIDAQmx_DO(OutputActuator):
    """One digital line: high for a value of 1 (from 0.5 on), low for 0. With ``pulse``, a move to 1 sets the line high
    for ``pulse_width`` ms and then low again, to trigger something (wire the line to a PFI terminal)."""
    _controller_units = ''
    _epsilons = [0.1]
    ui_type = UiType.BINARY  # two buttons: one for each level
    output_kind = ChannelKind.DO
    params = [
        {'title': 'Line:', 'name': 'channel', 'type': 'list', 'limits': [], 'tip': 'A digital line (Dev1/port0/line0)'},
        {'title': 'Pulse:', 'name': 'pulse', 'type': 'bool', 'value': False,
         'tip': 'A move to 1 sets the line high for the pulse width, then low again'},
        {'title': 'Pulse width (ms):', 'name': 'pulse_width', 'type': 'float', 'value': 10., 'min': 0.},
        {'title': 'Pulses sent:', 'name': 'pulses', 'type': 'int', 'value': 0, 'readonly': True,
         'tip': 'The line is low again after a pulse, so the position does not show it: this counts them'},
    ] + comon_parameters_fun(False, axis_names=OutputActuator._axis_names, epsilon=_epsilons)

    def make_task(self):
        return DigitalTask(TaskConfig(channels=[DigitalOut(self.settings['channel'])]))

    def send(self, level: float) -> None:
        high = bool(level >= 0.5)
        self.controller.write_digital(high)
        self.level = float(high)

    def show_settings(self) -> None:
        self.axis_unit = ''

    def drive(self, level: float) -> None:
        if self.settings['pulse'] and level >= 0.5:
            self.send(1.)
            time.sleep(self.settings['pulse_width'] * 1e-3)
            self.send(0.)
            self.target_value = DataActuator(data=0., units=self.axis_unit)  # the line is low again
            self.settings.child('pulses').setValue(self.settings['pulses'] + 1)
            self.emit_status(ThreadCommand('Update_Status', [
                f"Pulse {self.settings['pulses']} of {self.settings['pulse_width']:g} ms sent on "
                f"{self.settings['channel']}", 'log']))
        else:
            self.send(level)


if __name__ == '__main__':
    main(__file__)
