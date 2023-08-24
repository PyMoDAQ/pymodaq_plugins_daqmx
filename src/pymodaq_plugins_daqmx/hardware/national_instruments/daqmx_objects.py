from collections import OrderedDict
import numpy as np
import pymodaq_plugins_daqmx.hardware.national_instruments.daqmx as dq
from PyDAQmx import DAQmx_Val_FiniteSamps

from pymodaq.utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))

class AO_with_clock_DAQmx():
    """Object used to coordinate the use of several DAQmx by several modules.
    Its main intended use is to control the movement of several scanners (AO chans) with
    the timing given by the same clock channel."""
    def __init__(self):
        self.clock = dq.DAQmx()
        self.analog = dq.DAQmx()
        self.clock_channel_name = ''
        self.clock_channel = None
        self.clock_frequency = 100.0
        self.AO_channels = OrderedDict()
        self.num_ch = 0
        self.voltage_array = None
        self.max_ch_nb = 1
        self.applied_voltages = OrderedDict()
        self.locked = False  # True when busy already moving something

    def set_up_clock(self, nb_steps):
        """Prepare the clock with the desired frequency
        nb_steps (int) specifies the number of steps there will be in the movement."""
        self.clock_channel = dq.ClockCounter(self.clock_frequency,
                                             name=self.clock_channel_name,
                                             source="Counter")
        if self.clock.task is not None:
            self.clock.task.WaitUntilTaskDone(-1)  # in case another scanner is still moving
        self.clock.update_task(channels=[self.clock_channel])
        # we need to set the rate again, I do not understand why
        self.clock.task.SetSampClkRate(self.clock_frequency)
        self.clock.task.CfgImplicitTiming(DAQmx_Val_FiniteSamps, nb_steps + 1)

        clock_settings_ao = dq.ClockSettings(source="/" + self.clock_channel_name + "InternalOutput",
                                             frequency=self.clock_frequency,
                                             edge=dq.Edge.names()[0],
                                             Nsamples=nb_steps + 1,
                                             repetition=False)
        self.get_max_ch_nb()
        return clock_settings_ao

    def update_ao_channels(self, channel, axis, clock_settings_ao):
        """Update the dict containing the AO channels, and the associated task in the
        corresponding DAQmx object."""
        self.AO_channels[axis] = channel
        if axis not in self.applied_voltages.keys():
            self.applied_voltages[axis] = 0.0
        self.num_ch = len(self.AO_channels)
        self.get_max_ch_nb()
        if self.num_ch > self.max_ch_nb:
            logger.info("Too many AO channels!")
            return
        if self.clock.task is not None:  # we wait for slow movements
            print("clock done", self.clock.isTaskDone())
            self.clock.task.WaitUntilTaskDone(-1)  # in case another scanner is still moving
        self.analog.update_task(channels=[self.AO_channels[ax] for ax in self.AO_channels.keys()],
                                clock_settings=clock_settings_ao)

    def set_up_voltage_array(self, voltage_list, axis):
        print("moving axis", axis)
        if self.num_ch == 1:
            self.voltage_array = voltage_list
        elif self.num_ch > 1:
            self.voltage_array = np.zeros((self.num_ch, len(voltage_list)))
            for i, ax in enumerate(self.AO_channels.keys()):
                if ax == axis:
                    self.voltage_array[i, :] = voltage_list
                else:
                    # we need to keep the other scanners were they are
                    self.voltage_array[i, :] = self.applied_voltages[ax] * np.ones(len(voltage_list))

    def write_voltages(self):
        """Actually writes the voltages"""
        if len(np.shape(self.voltage_array)) > 1:
            nb_steps = np.size(self.voltage_array, axis=1)
        else:
            nb_steps = len(self.voltage_array)

        # store last values of the lists as applied voltage
        axes = [ax for ax in self.applied_voltages.keys()]
        if len(axes) == 1:
            self.applied_voltages[axes[0]] = self.voltage_array[-1]
        elif len(axes) > 1:
            for i in range(len(axes)):
                self.applied_voltages[axes[i]] = self.voltage_array[i, -1]

        self.analog.start()
        print('writing voltages')
        self.analog.writeAnalog(nb_steps, self.num_ch, self.voltage_array)

    def get_max_ch_nb(self):
        # get the max number of available AO channels of the device with the clock
        dev = self.clock_channel_name.split('/')[0]
        chans = self.clock.get_NIDAQ_channels(devices=[dev], source_type="Analog_Output")
        self.max_ch_nb = len(chans)

    def stop(self):
        self.locked = False
        self.clock.stop()
        self.analog.stop()
