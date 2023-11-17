import numpy as np
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataWithAxes, DataToExport, DataSource
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter

from pymodaq_plugins_daqmx.hardware.national_instruments.daqmx import DAQmx, \
    Edge, ClockSettings, Counter, ClockCounter,  TriggerSettings

from PyDAQmx import DAQmx_Val_ContSamps

class DAQ_0DViewer_DAQmx_counter(DAQ_Viewer_base):
    """
    Plugin for a 0D PL counter, based on a NI card.
    """
    params = comon_parameters+[
        {"title": "Counting channel:", "name": "counter_channel",
         "type": "list", "limits": DAQmx.get_NIDAQ_channels(source_type="Counter")},
        {"title": "Acq. Time (s):", "name": "acq_time",
         "type": "float", "value": 1., "default": 1.},
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
        if param.name() == "acq_time":
            self.counting_time = param.value()
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
            info = "NI card based counter"
            self.counting_time = self.settings.child("acq_time").value()
        except Exception as e:
            print(e)
            initialized = False
            info = "Error"
            
        self.dte_signal_temp.emit(DataToExport(name='PL',
                                               data=[DataWithAxes(name='Counts', data=[np.array([0])],
                                               source=DataSource['raw'],
                                               dim='Data0D', labels=['counts (Hz)'])]))
        
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
        update = True  # to decide if we do the initial set up or not

        if 'live' in kwargs:
            if kwargs['live'] == self.live and self.live:
                update = False  # we are already live
            self.live = kwargs['live']
            
        if update:
            self.update_tasks()
            self.controller["clock"].start()
        
        read_data = self.controller["counter"].readCounter(1, counting_time=self.counting_time)
        data_pl = read_data/self.counting_time  # convert to kcts/s
        self.dte_signal.emit(DataToExport(name='PL',
                                          data=[DataWithAxes(name='PL', data=[data_pl],
                                                             source=DataSource['raw'],
                                                             dim='Data0D', labels=['PL (kcts/s)'])]))

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        self.close()
        self.emit_status(ThreadCommand('Update_Status', ['Acquisition stopped.']))
        return ''

    def update_tasks(self):
        """Set up the counting tasks in the NI card."""
        # Create channels
        self.clock_channel = ClockCounter(1/self.settings.child("acq_time").value(),
                                          name=self.settings.child("clock_channel").value(),
                                          source="Counter")
        self.counter_channel = Counter(name=self.settings.child("counter_channel").value(),
                                       source="Counter", edge=Edge.names()[0])

        self.controller["clock"].update_task(channels=[self.clock_channel],
                                             clock_settings=ClockSettings(),
                                             trigger_settings=TriggerSettings())
        self.controller["clock"].task.CfgImplicitTiming(DAQmx_Val_ContSamps, 1)
        
        self.controller["counter"].update_task(channels=[self.counter_channel],
                                               clock_settings=ClockSettings(),
                                               trigger_settings=TriggerSettings())

        # connect the clock to the counter
        self.controller["counter"].task.SetSampClkSrc("/" + self.clock_channel.name + "InternalOutput")

        
if __name__ == '__main__':
    main(__file__)
