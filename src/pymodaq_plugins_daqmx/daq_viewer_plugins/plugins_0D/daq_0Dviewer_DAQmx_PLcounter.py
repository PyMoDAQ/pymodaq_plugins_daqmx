import numpy as np
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataFromPlugins
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter

from pymodaq_plugins_daqmx.hardware.national_instruments.daqmx import DAQmx, \
    Edge, ClockSettings, ClockCounter, SemiPeriodCounter, TriggerSettings

from PyDAQmx import DAQmx_Val_DoNotInvertPolarity, \
     DAQmx_Val_ContSamps, DAQmx_Val_FiniteSamps, DAQmx_Val_CurrReadPos, \
     DAQmx_Val_DoNotOverwriteUnreadSamps

class DAQ_0DViewer_DAQmx_PLcounter(DAQ_Viewer_base):
    """
    Plugin for a 0D PL counter, based on a NI card.
    """
    params = comon_parameters+[
       {"title": "Counting channel:", "name": "counter_channel",
          "type": "list", "limits": DAQmx.get_NIDAQ_channels(source_type="Counter")},
        {"title": "Source settings:", "name": "source_settings",
           "type": "group", "visible": True, "children": [
             {"title": "Enable?:", "name": "enable", "type": "bool",
                "value": False, },
             {"title": "Photon source:", "name": "photon_channel",
                "type": "list", "limits": DAQmx.getTriggeringSources()},
             {"title": "Edge type:", "name": "edge", "type": "list",
                "limits": Edge.names(), "visible": False},
             {"title": "Level:", "name": "level", "type": "float",
                "value": 1., "visible": False}]
         },
        {"title": "Clock frequency (Hz):", "name": "clock_freq",
            "type": "float", "value": 100., "default": 100., "min": 1},
        {'title': 'Clock channel:', 'name': 'clock_channel', 'type': 'list',
             'limits': DAQmx.get_NIDAQ_channels(source_type='Counter')},
        ]

    def ini_attributes(self):
        self.controller = None
        self.clock_channel = None
        self.counter_channel = None
        self.live = False  # True during a continuous grab
        self.counting_time = 0.1

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        if param.name() == "clock_freq":
            self.counting_time = 1/param.value()
        else:
            self.stop()
            self.update_tasks()
       

    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator/detector by controller
            (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        self.controller = {"clock": DAQmx(), "counter": DAQmx()}
        try:
            self.update_tasks()
            initialized = True
            info = "NI card based PL counter"
        except Exception as e:
            print(e)
            initialized = False
            info = "Error"
            
        self.data_grabed_signal_temp.emit([DataFromPlugins(name='PL',data=[np.array([0])],
                                                           dim='Data0D', labels=['PL (kcts/s)'])])
        return info, initialized
    
    def close(self):
        """Terminate the communication protocol"""
        self.controller["clock"].close()
        self.controller["counter"].close()
        
    def grab_data(self, Naverage=1, **kwargs):
        """Start a grab from the detector

        Parameters
        ----------
        Naverage: int
            Number of hardware averaging not relevant here.
        kwargs: dict
            others optionals arguments
        """
        # update = True  # to decide if we do the initial set up or not

        # if 'live' in kwargs:
        #     if kwargs['live'] == self.live and self.live:
        #         update = False  # we are already live
        #     self.live = kwargs['live']
            
        #if update:
        self.update_tasks()
            
        self.controller["clock"].stop() # to ensure that the clock is available
        self.controller["clock"].task.CfgImplicitTiming(DAQmx_Val_FiniteSamps, 1000)

        try:
            timeout = 2
            self.controller["clock"].start()
            #self.controller["clock"].task.WaitUntilTaskDone(timeout*2)
        except Exception as e:
            print(e)
            self.emit_status(ThreadCommand('Update_Status',
                                               ['Cannot start the counter clock']))
            return
        
        self.controller["counter"].task.CfgImplicitTiming(DAQmx_Val_ContSamps, 1000)
        self.controller["counter"].task.SetReadRelativeTo(DAQmx_Val_CurrReadPos)
        self.controller["counter"].task.SetReadOffset(0)
        self.controller["counter"].task.SetReadOverWrite(DAQmx_Val_DoNotOverwriteUnreadSamps)
        
        try:
            self.controller["counter"].start()
        except Exception as e:
            print(e)
            self.emit_status(ThreadCommand('Update_Status',
                                               ['Cannot start the PL counter']))
                
        print("ready to read")
        read_data = self.controller["counter"].readCounter(2, counting_time=self.counting_time,
                                                           read_function="")
        print(read_data)
        data_pl = 1e-3*np.sum(read_data)/self.counting_time
            
        self.data_grabed_signal.emit([DataFromPlugins(name='PL', data=[data_pl],
                                                      dim='Data0D', labels=['PL (kcts/s)'])])

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        self.close()
        self.emit_status(ThreadCommand('Update_Status', ['Acquisition stopped.']))
        return ''

    def update_tasks(self):
        """Set up the counting tasks in the NI card."""
        # Create channels
        self.create_channels()
        # configure tasks
        self.configure_tasks()
        # connect everything
        self.connect_channels()

    def create_channels(self):
        """ Create the channels in the NI card to update the tasks."""
        clock_freq = self.settings.child("clock_freq").value()
        self.clock_channel = ClockCounter(clock_freq,
                                          name=self.settings.child("clock_channel").value(),
                                          source="Counter")
        
        self.counter_channel = SemiPeriodCounter(5e6,
                                    name=self.settings.child("counter_channel").value(),
                                    source="Counter")
       
    def configure_tasks(self):
        """ Configure the tasks in the NI card, by calling the update functions of each controller."""
        self.controller["clock"].update_task(channels=[self.clock_channel],
                                             # do not configure clock yet, so Nsamples=1
                                             clock_settings=ClockSettings(Nsamples=1),
                                             trigger_settings=TriggerSettings())
        self.controller["counter"].update_task(channels=[self.counter_channel],
                                               clock_settings=ClockSettings(Nsamples=1),
                                               trigger_settings=TriggerSettings())
        
    def connect_channels(self):
        """ Connect together the channels for synchronization."""
        # connect the pulses from the clock to the counter
        self.controller["counter"].task.SetCISemiPeriodTerm(self.counter_channel.name,
                                                '/'+self.clock_channel.name + "InternalOutput")
        # define the source of ticks for the counter 
        self.controller["counter"].task.SetCICtrTimebaseSrc(self.counter_channel.name,
                            self.settings.child("source_settings", "photon_channel").value())
        
        
if __name__ == '__main__':
    main(__file__)
