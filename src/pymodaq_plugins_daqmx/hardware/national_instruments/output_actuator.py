"""Base class of the actuators that drive one output of an NI device, one point at a time.

The output is driven on demand: there is no clock and no waveform. The level of an output cannot be read back, so the
position is the last level written. The output goes to 0 when the actuator starts, when its channel changes and when it
closes. The analog and the digital actuators (``DAQ_Move_NIDAQmx``, ``DAQ_Move_NIDAQmx_DO``) share all of this and only
differ by their settings, their task and the way a level is written.
"""
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, DataActuator, DataActuatorType
from pymodaq.utils.logger import get_module_name, set_logger

from pymodaq_plugins_daqmx.hardware.national_instruments.api import ChannelKind, NIDAQSystem

logger = set_logger(get_module_name(__file__))


class OutputActuator(DAQ_Move_base):
    """One output of an NI device. A subclass gives ``output_kind`` (the outputs offered), ``rebuild_on`` (the
    settings that need a new task) and the methods ``make_task``, ``send`` and ``show_settings``."""
    is_multiaxes = False
    _axis_names = ['output']
    data_actuator_type = DataActuatorType.DataActuator
    output_kind = ChannelKind.AO
    rebuild_on = ('channel',)  # the settings that need a new task when they change

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings.child('channel').setLimits(NIDAQSystem().all_channels(self.output_kind))
        self.show_settings()

    def ini_attributes(self):
        self.controller = None  # the task of the output
        self.level = 0.  # the last level written

    # --- what a subclass gives ----------------------------------------------------------------------------------

    def make_task(self):
        """The task of the chosen output, built from the settings."""
        raise NotImplementedError

    def send(self, level: float) -> None:
        """Drive the output to ``level`` on the task and keep it in ``self.level``."""
        raise NotImplementedError

    def show_settings(self) -> None:
        """Show the settings that apply to the output, and set the unit of the actuator."""
        raise NotImplementedError

    def clip(self, level: float) -> float:
        """The level that the output can take (an analog output has a range)."""
        return level

    def drive(self, level: float) -> None:
        """Bring the output to ``level`` (a digital line can pulse instead): sets ``self.target_value`` if it differs."""
        self.send(level)

    # --- the output ---------------------------------------------------------------------------------------------

    def open_output(self) -> None:
        """Make the task of the chosen output and set the output to 0."""
        self.controller = self.make_task()
        self.send(0.)

    def close_output(self) -> None:
        """Set the output to 0 and release it: the channel is the one of this task only while it is open."""
        if self.controller is None:
            return
        try:
            self.send(0.)
        except Exception:  # closing must go on: the channel has to be released
            logger.warning('The output could not be set to 0', exc_info=True)
        self.controller.close()
        self.controller = None

    # --- the actuator -------------------------------------------------------------------------------------------

    def ini_stage(self, controller=None):
        self.show_settings()  # the settings may have been given before the initialization
        self.open_output()
        return 'NI output ready', True

    def close(self):
        self.close_output()

    def commit_settings(self, param):
        if param.name() in self.rebuild_on and self.controller is not None:
            self.close_output()  # the old output goes to 0 before the new one is driven
            self.show_settings()
            self.open_output()
        elif param.name() in self.rebuild_on:
            self.show_settings()

    def get_actuator_value(self) -> DataActuator:
        return DataActuator(data=self.level, units=self.axis_unit)

    def move_abs(self, value: DataActuator):
        value = self.check_bound(value)
        level = self.clip(float(value.value(self.axis_unit)))
        self.target_value = DataActuator(data=level, units=self.axis_unit)
        self.drive(level)

    def move_rel(self, value: DataActuator):
        self.move_abs(DataActuator(data=self.level + float(value.value(self.axis_unit)), units=self.axis_unit))

    def move_home(self):
        self.move_abs(DataActuator(data=0., units=self.axis_unit))

    def stop_motion(self):
        pass  # a level is written at once: there is nothing to stop
