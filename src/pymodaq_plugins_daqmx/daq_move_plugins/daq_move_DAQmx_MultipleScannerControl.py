import numpy as np
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters_fun, main  # common set of
# parameters for all actuators
from pymodaq.utils.daq_utils import ThreadCommand # object used to send info back to the main thread
from pymodaq.utils.parameter import Parameter

from pymodaq_plugins_daqmx.hardware.national_instruments.daqmx import DAQmx, AOChannel, \
    ClockSettings, DAQ_analog_types, ClockCounter, Edge

from PyDAQmx import DAQmx_Val_FiniteSamps

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
    is_multiaxes = False  
    axes_names = [ ]
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
        self.clock = None
        self.step_size = 100.0  # in nm! be careful with the scaling param
        self.step_time = 10e-3
        self.number_steps = 1
        self.conv_factor = 7500.0
        self.clock_channel = None
        self.scanner_channel = None
        self.voltage_list = np.array([0.0])
        self.init_step_index = 0

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
                self.clock.task.GetCOCount(self.clock_channel.name, PyDAQmx.byref(current_step_index))
                index = self.init_step_index - current_step_index.value
                voltage = self.voltage_list[min(int(index/2), len(self.voltage_list)-1)]
            except:  # when the task did not start
                voltage = self.voltage_list[0]
        
        # if we do only one step, we do not care, there is no timing anyway.
        else:
            voltage = self.controller.get_last_write()
        # convert voltage to position
        pos = voltage * self.conv_factor
        pos = self.get_position_with_scaling(pos)
        return pos

    def close(self):
        """ Terminate the communication protocol"""
        print("move_done received, closing task")
        self.clock.close()
        self.controller.close()

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        if param.name() == "analog_channel":
            self.close()
            self.update_task()
        elif param.name() == "clock_channel":
            self.close()
            self.update_task()
        elif param.name() == "step_size":
            self.step_size = param.value()
        elif param.name() == "step_time":
            self.step_time = param.value()*1e-3
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
        self.controller = DAQmx()
        self.clock = DAQmx()
        self.step_size = self.settings.child("step_size").value()
        # Step time is given in ms by the user
        self.step_time = self.settings.child("step_time").value()*1e-3
        self.conv_factor = self.settings.child("conv_factor").value()

        # we need to close the clock once the move is done, to free
        # the counter resource
        self.move_done_signal.connect(self.close)
        
        try:
            self.update_task()
            initialized = True
            info = "NI card based piezo scanner control."
            self.move_abs(0.0)  # to avoid bad initial positioning because
            # we can't read the actual value from the NI card.
        except Exception as e:
            print(e)
            initialized = False
            info = "Error"
    
        return info, initialized

    def move_abs(self, value):
        """ Move the actuator to the absolute target defined by value

        Parameters
        ----------
        value: (float) value of the absolute target positioning 
        """
        if value == 0.0:
            value = 1.0
        self.close()
        value = self.check_bound(value)  # if user checked bounds, the defined bounds are applied here
        self.target_value = value
        value = self.set_position_with_scaling(value)  # apply scaling if the user specified one
        self.move_scanner()
        self.emit_status(ThreadCommand('Update_Status', ['Absolute movement.']))

    def move_rel(self, value):
        """ Move the actuator to the relative target actuator value defined by value

        Parameters
        ----------
        value: (float) value of the relative target positioning
        """
        self.close()
        value = self.check_bound(self.current_value + value) - self.current_value
        self.target_value = value + self.current_value
        if self.target_value == 0.0:
            self.target_value = 1.0
        value = self.set_position_relative_with_scaling(value)
        self.move_scanner()
        self.emit_status(ThreadCommand('Update_Status', ['Relative movement.']))

    def move_home(self):
        """Do nothing"""
        self.emit_status(ThreadCommand('Update_Status', ['No home position implemented.']))

    def stop_motion(self):
      """Stop the actuator and emits move_done signal"""
      self.close()
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

        # If we do more than one step, we need a clock for the time sampling
        # because we want a smooth and slow movement.
        if len(self.voltage_list) > 1:
            self.clock_channel = ClockCounter(1/self.step_time,
                                              name=self.settings.child("clock_channel").value(),
                                              source="Counter")
            self.clock.update_task(channels=[self.clock_channel])
            # we need to set the rate again, I do not understand why
            self.clock.task.SetSampClkRate(1/self.step_time) 
            self.clock.task.CfgImplicitTiming(DAQmx_Val_FiniteSamps, self.number_steps+1)
           
            clock_settings_ao = ClockSettings(source="/" + self.clock_channel.name + "InternalOutput",
                                              frequency=1/self.step_time,
                                              edge=Edge.names()[0],
                                              Nsamples=len(self.voltage_list)+1,
                                              repetition=False)
        else:
            # empty clock settings if we do only one step
            clock_settings_ao = ClockSettings(source=None,
                                              frequency=1/self.step_time,
                                              Nsamples=1,
                                              edge=Edge.names()[0],
                                              repetition=False)
            
        self.controller.update_task(channels=[self.scanner_channel],
                                    clock_settings=clock_settings_ao)

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

    def move_scanner(self):
        """ Actually moves the scanner. """
        # compute the path
        self.prepare_voltage_list()
        # prepare the tasks
        self.update_task()
        if len(self.voltage_list) > 1:
            #self.controller.task.SetSampTimingType(DAQmx_Val_SampClk)
            self.clock.start()
            self.init_step_index = 2*len(self.voltage_list)+1
            
        # Actually tells the NI card to send the list of voltages.
        self.controller.start()
        self.controller.writeAnalog(self.number_steps, 1, self.voltage_list)
            
    
if __name__ == '__main__':
    main(__file__)
