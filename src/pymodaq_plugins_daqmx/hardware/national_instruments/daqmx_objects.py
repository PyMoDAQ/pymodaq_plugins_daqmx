import PyDAQmx
import ctypes
import numpy as np
import pymodaq_plugins_daqmx.hardware.national_instruments.daqmx as dq
from PyDAQmx import DAQmx_Val_FiniteSamps

from pymodaq.utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))

class AO_with_clock_DAQmx:
    """Object used to coordinate the use of several DAQmx by several modules.
    Its main intended use is to control the movement of several scanners (AO chans) with
    the timing given by the same clock channel."""
    def __init__(self):
        self.clock = dq.DAQmx()
        self.analog = dq.DAQmx()
        self.clock_channel_name = ''
        self.clock_channel = None
        self.clock_frequency = 100.0
        self.AO_channels = {}
        self.num_ch = 0
        self.voltage_array = None

    def set_up_clock(self, nb_steps):
        """Prepare the clock with the desired frequency
        nb_steps (int) specifies the number of steps there will be in the movement."""
        self.clock_channel = dq.ClockCounter(self.clock_frequency,
                                             name=self.clock_channel_name,
                                             source="Counter")
        self.clock.update_task(channels=[self.clock_channel])
        # we need to set the rate again, I do not understand why
        self.clock.task.SetSampClkRate(self.clock_frequency)
        self.clock.task.CfgImplicitTiming(DAQmx_Val_FiniteSamps, nb_steps + 1)

        clock_settings_ao = dq.ClockSettings(source="/" + self.clock_channel_name + "InternalOutput",
                                             frequency=self.clock_frequency,
                                             edge=dq.Edge.names()[0],
                                             Nsamples=nb_steps + 1,
                                             repetition=False)
        return clock_settings_ao

    def update_ao_channels(self, channel, axis, clock_settings_ao):
        """Update the dict containing the AO channels, and the associated task in the
        corresponding DAQmx object."""
        self.AO_channels[axis] = channel
        self.num_ch = len(self.AO_channels)
        self.analog.update_task(channels=[self.AO_channels[ax] for ax in self.AO_channels.keys()],
                                clock_settings=clock_settings_ao)

    def set_up_voltage_array(self, voltage_list, axis):
        pass

    def write_voltages(self):
        """Actually writes the voltages"""
        nb_steps = np.size(self.voltage_array, axis=0)
        self.analog.start()
        self.analog.writeAnalog(nb_steps, self.num_ch, self.voltage_array)

