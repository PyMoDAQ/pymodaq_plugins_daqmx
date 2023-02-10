import numpy as np
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataFromPlugins
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter

from pymodaq_plugins_daqmx.hardware.national_instruments.daqmx import DAQmx, \
    Edge, ClockSettings, Counter,  TriggerSettings

# from PyDAQmx import DAQmx_Val_DoNotInvertPolarity, \
#      DAQmx_Val_ContSamps, DAQmx_Val_FiniteSamps, DAQmx_Val_CurrReadPos, \
#      DAQmx_Val_DoNotOverwriteUnreadSamps

class DAQ_0DViewer_DAQmx_PLcounter(DAQ_Viewer_base):
    """
    Plugin for a 0D PL counter, based on a NI card.
    """
    params = comon_parameters+[
       {"title": "Counting channel:", "name": "counter_channel",
          "type": "list", "limits": DAQmx.get_NIDAQ_channels(source_type="Counter")},
        {"title": "Photon source:", "name": "photon_channel",
         "type": "list", "limits": DAQmx.getTriggeringSources()},
        {"title": "Clock frequency (Hz):", "name": "clock_freq",
            "type": "float", "value": 100., "default": 100., "min": 1},
        {'title': 'Clock channel:', 'name': 'clock_channel', 'type': 'list',
             'limits': DAQmx.get_NIDAQ_channels(source_type='Counter')}
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
            
        # if update:
        self.update_tasks()
            
        read_data = self.controller["counter"].readCounter(1, counting_time=self.counting_time)
        print(read_data)
        data_pl = 1e-3*read_data/self.counting_time
        self.data_grabed_signal.emit([DataFromPlugins(name='PL', data=[data_pl],
                                                      dim='Data0D', labels=['PL (kcts/s)'])])

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        self.close()
        self.emit_status(ThreadCommand('Update_Status', ['Acquisition stopped.']))
        return ''

    def update_tasks(self):
        """Set up the counting tasks in the NI card."""
        # Create channel
        self.counter_channel = Counter(name=self.settings.child("counter_channel").value(),
                                       source="Counter", edge=Edge.names()[0])

        self.controller["counter"].update_task(channels=[self.counter_channel],
                                               clock_settings=ClockSettings(
                                                   source=self.settings.child("clock_channel").value(),
                                                   frequency=self.settings.child("clock_freq").value(),
                                                   edge=Edge.names()[0],
                                                   repetition=True,
                                                   Nsamples=1),
                                               trigger_settings=TriggerSettings(
                                                   trig_source=self.settings.child("photon_channel").value(),
                                                   enable=True,
                                                   edge=Edge.names()[0],
                                                   level=0.5)
                                               )
        
        
if __name__ == '__main__':
    main(__file__)
