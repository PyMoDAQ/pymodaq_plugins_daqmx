import numpy as np
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters_fun, main  # common set of
# parameters for all actuators
from pymodaq.utils.daq_utils import ThreadCommand # object used to send info back to the main thread
from pymodaq.utils.parameter import Parameter

from pymodaq_plugins_daqmx.hardware.national_instruments.daqmx_objects import AO_with_clock_DAQmx

from pymodaq_plugins_daqmx.hardware.national_instruments.daqmx import DAQmx, AOChannel, \
    ClockSettings, DAQ_analog_types, Edge

import PyDAQmx

class DAQ_Move_DAQmx_MultipleScannerControl(DAQ_Move_base):
    """Plugin to control a piezo scanners with a NI card. This modules requires a clock channel to handle the
    timing of the movement and display the position, and this clock channel is shared between the master and
    the slave daq_move created with this module, to allow smooth movements.

    This object inherits all functionality to communicate with PyMoDAQ Module through inheritance via DAQ_Move_base
    It then implements the particular communication with the instrument.

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library

    """
    _controller_units = 'nm'  
    is_multiaxes = True
    axes_names = ['x', 'y', 'z']
    _epsilon = 10

    params = [ {"title": "Output channel:", "name": "analog_channel",
                "type": "list", "limits": DAQmx.get_NIDAQ_channels(source_type="Analog_Output")},
               {'title': 'Clock channel:', 'name': 'clock_channel', 'type': 'list',
                'limits': DAQmx.get_NIDAQ_channels(source_type='Counter')},
               {"title": "Step size (nm)", "name": "step_size", "type": "float", "value": 100.0},
               {"title": "Step time (ms)", "name": "step_time", "type": "float", "value": 10.0},
               {"title": "Conversion factor (nm/V)", "name": "conv_factor", "type": "float", "value": 7500.0}
                ] + comon_parameters_fun(is_multiaxes, axes_names)

    def ini_attributes(self):
        self.controller = None
        self.step_size = 100.0  # in nm! be careful with the scaling param
        self.number_steps = 1
        self.conv_factor = 7500.0
        self.scanner_channel = None
        self.voltage_list = np.array([0.0])
        self.init_step_index = 0
        self.waiting_to_move = [False, "abs"]

    def get_actuator_value(self):
        """Get the current value from the hardware with scaling conversion.
        Reading the actual state is tricky with the NI card because the list of voltages
        is sent in the buffer immediately, so reading the last written voltage always 
        yield the target value, independently of the clock timing. 
        To bypass this issue, instead of reading the written voltage, we read the current 
        clock index and use it to retrieve the corresponding voltage from our list.
        Beware that the index given by GetCOCount start at a value 2*nb_voltages + 1
        and decreases. Therefore, we store the first value returned in self.init_step_index
        and use this as a starting point.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """
        if len(self.voltage_list) > 1:
            try:
                current_step_index = PyDAQmx.c_ulong()
                self.controller.clock.task.GetCOCount(self.controller.clock_channel_name,
                                                      PyDAQmx.byref(current_step_index))
                index = self.init_step_index - current_step_index.value
                voltage = self.voltage_list[min(int(index/2), len(self.voltage_list)-1)]
            except:  # when the task did not start
                voltage = self.voltage_list[0]
        
        # if we do only one step, we do not care, there is no timing anyway.
        else:
            voltage = self.controller.applied_voltages[self.settings.child('multiaxes', 'axis').value()]
        # convert voltage to position
        pos = voltage * self.conv_factor
        pos = self.get_position_with_scaling(pos)
        return pos

    def close(self):
        """ Terminate the communication protocol"""
        # This might be brutal if we are controlling another axis at the same time
        self.controller.clock.close()
        self.controller.analog.close()

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        if param.name() == "analog_channel":
            self.update_task()
        elif param.name() == "clock_channel":
            self.controller.clock_channel_name = self.settings.child("clock_channel").value()
            self.update_task()
        elif param.name() == "step_size":
            self.step_size = param.value()
        elif param.name() == "step_time":
            self.controller.clock_frequency = 1e3 / self.settings.child("step_time").value()  # time give in ms
        elif param.name() == "conv_factor":
            self.conv_factor = param.value()

    def ini_stage(self, controller=None):
        """Actuator communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case).
            None if only one actuator by controller (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        # we need a clock task and analog output task.
        # The analog output can handle several channels, for the different axis
        self.controller = self.ini_stage_init(old_controller=controller,
                                              new_controller=AO_with_clock_DAQmx())

        self.step_size = self.settings.child("step_size").value()
        self.conv_factor = self.settings.child("conv_factor").value()

        # Step time is given in ms by the user
        # Clock channel and step time should only be modified on the master actuator
        # because the clock is shared. If not master, these parameters are hidden.
        if self.settings.child("multiaxes", "multi_status").value() == "Master":
            self.controller.clock_frequency = 1e3 / self.settings.child("step_time").value()  # time give in ms
            self.controller.clock_channel_name = self.settings.child("clock_channel").value()
        else:
            self.settings.child("step_time").hide()
            self.settings.child("clock_channel").hide()

        self.move_done_signal.connect(self.controller.received_move_done)
        self.controller.ni_card_ready_for_moving.connect(self.finish_waiting)
        
        try:
            self.update_task()
            initialized = True
            info = "NI card based piezo scanner control."
            self.move_abs(0.0, init=True)  # to avoid bad initial positioning because
            # we can't read the actual value from the NI card.
        except Exception as e:
            print(e)
            initialized = False
            info = "Error"
    
        return info, initialized

    def move_abs(self, value, init=False):
        """ Move the actuator to the absolute target defined by value

        Parameters
        ----------
        value: (float) value of the absolute target positioning 
        """
        if value == 0.0:
            value = 1.0  # using 0.0 creates issues
        value = self.check_bound(value)  # if user checked bounds, the defined bounds are applied here
        self.target_value = value
        self.set_position_with_scaling(value)  # apply scaling if the user specified one
        # check if we are already there
        if np.abs(self.current_value - self.target_value) < self._epsilon and not init:
            # already there
            self.emit_status(ThreadCommand('Update_Status', ['Already there.']))
            return
        else:
            if not self.controller.locked or init:
                self.move_scanner(init=init)
                self.emit_status(ThreadCommand('Update_Status', ['Absolute movement.']))
            else:
                self.waiting_to_move = [True, "abs"]

    def move_rel(self, value):
        """ Move the actuator to the relative target actuator value defined by value

        Parameters
        ----------
        value: (float) value of the relative target positioning
        """
        if np.abs(value) < self._epsilon:
            # already there
            self.emit_status(ThreadCommand('Update_Status', ['Already there.']))
            return
        else:
            value = self.check_bound(self.current_value + value) - self.current_value
            self.target_value = value + self.current_value
            if self.target_value == 0.0:
                self.target_value = 1.0
            self.set_position_relative_with_scaling(value)
            if not self.controller.locked:
                self.move_scanner()
                self.emit_status(ThreadCommand('Update_Status', ['Relative movement.']))
            else:
                self.waiting_to_move = [True, "rel"]

    def move_home(self):
        """Do nothing"""
        self.emit_status(ThreadCommand('Update_Status', ['No home position implemented.']))

    def stop_motion(self):
        """Stop the actuator and emits move_done signal"""
        self.controller.locked = False
        self.waiting_to_move[0] = False
        self.controller.stop()
        self.emit_status(ThreadCommand('Update_Status', ['Motion stopped.']))

    def update_task(self):
        """ Set up the analog output task in the NI card, and the clock if necessary."""
        min_voltage = self.settings.child("bounds", "min_bound").value()/self.conv_factor
        max_voltage = self.settings.child("bounds", "max_bound").value()/self.conv_factor
        self.scanner_channel = AOChannel(name=self.settings.child("analog_channel").value(),
                                         source="Analog_Output",
                                         analog_type=DAQ_analog_types.names()[0],
                                         value_min=min_voltage,
                                         value_max=max_voltage)

        # If we do more than one step, we need the clock for the time sampling
        # because we want a smooth and slow movement.
        if len(self.voltage_list) > 1:
            clock_settings_ao = self.controller.set_up_clock(self.number_steps)
        else:
            # empty clock settings if we do only one step
            clock_settings_ao = ClockSettings(source=None,
                                              frequency=1/self.controller.clock_frequency,
                                              Nsamples=1,
                                              edge=Edge.names()[0],
                                              repetition=False)

        self.controller.update_ao_channels(self.scanner_channel,
                                           self.settings.child('multiaxes', 'axis').value(),
                                           clock_settings_ao)

    def prepare_voltage_list(self):
        """Generates the list of voltages to move smoothly the scanner."""
        # if the desired step size is larger than the movement to realize, only one value
        if np.abs(self.target_value - self.current_value) <= self.step_size:
            self.voltage_list = np.array([self.target_value])/self.conv_factor
        # otherwise we do steps
        else:
            pos_list = np.arange(min(self.current_value, self.target_value),
                                 max(self.current_value, self.target_value)+self.step_size,
                                 self.step_size)
            # we need to start from the beginning
            if pos_list[0] != self.current_value:
                pos_list = pos_list[::-1]

            # we ensure that the last value is the target, otherwise we might get caught in a loop
            # if the position goes to target from more than epsilon.
            pos_list[-1] = self.target_value
            
            # convert to voltage
            self.voltage_list = pos_list/self.conv_factor
        self.number_steps = len(self.voltage_list)

    def move_scanner(self, init=False):
        """ Actually moves the scanner. """
        # compute the path
        self.prepare_voltage_list()
        if not init:
            self.controller.locked = True
        # fill with zeros according to the other AO channels in the controller
        self.controller.set_up_voltage_array(self.voltage_list,
                                             self.settings.child('multiaxes', 'axis').value())
        # prepare the tasks
        self.update_task()
        if self.number_steps > 1:
            self.controller.clock.start()
            self.init_step_index = 2*len(self.voltage_list)+1
            
        # Actually tells the NI card to send the list of voltages.
        self.controller.write_voltages()

    def finish_waiting(self):
        if self.waiting_to_move[0]:
            self.move_scanner()
            if self.waiting_to_move[1] == "abs":
                self.emit_status(ThreadCommand('Update_Status', ['Absolute movement.']))
            elif self.waiting_to_move[1] == "rel":
                self.emit_status(ThreadCommand('Update_Status', ['Relative movement.']))
            self.waiting_to_move[0] = False

    
if __name__ == '__main__':
    main(__file__)
