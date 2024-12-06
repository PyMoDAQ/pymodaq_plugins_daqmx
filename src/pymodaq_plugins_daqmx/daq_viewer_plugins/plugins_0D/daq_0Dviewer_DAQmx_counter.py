import numpy as np
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataWithAxes, DataToExport, DataSource
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter
import nidaqmx

from pymodaq_plugins_daqmx.hardware.national_instruments.daqmxni import DAQmx, Edge, Counter


class DAQ_0DViewer_DAQmx_counter(DAQ_Viewer_base):
    """
    Plugin for a 0D PL counter, based on a NI card.
    """
    params = comon_parameters+[
        {"title": "Counting channel:", "name": "counter_channel",
         "type": "list", "limits": DAQmx.get_NIDAQ_channels(source_type="Counter")},
        {"title": "Acq. Time (s):", "name": "acq_time",
         "type": "float", "value": 1., "default": 1.},
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
        self.controller = DAQmx() #{"clock": DAQmx(), "counter": DAQmx()}
        try:
            self.update_tasks()
            initialized = True
            info = "NI card based counter"
            self.counting_time = self.settings.child("acq_time").value()
        except Exception as e:
            print(e)
            initialized = False
            info = "Error"

        return info, initialized

    def close(self):
        """Terminate the communication protocol"""
        pass
        #self.controller["clock"].close()
        #self.controller["counter"].close()

    def grab_data(self, Naverage=1, **kwargs):
        """Start a grab from the detector

        Parameters
        ----------
        Naverage: int
            Number of hardware averaging not relevant here.
        kwargs: dict
            others optionals arguments
        """
        #update = False  # to decide if we do the initial set up or not


        #if 'live' in kwargs:
        #    if kwargs['live'] != self.live:
        #        update = True
        #    self.live = kwargs['live']
        #    """
        #if 'live' in kwargs:
        #    if kwargs['live'] == self.live:
        #        update = False  # we are already live
        #    self.live = kwargs['live']
        #    """

        #if update:
        #    self.update_tasks()
        #    self.controller["clock"].start()

        read_data = 32#self.controller.readCounter()#, counting_time=self.counting_time)
        data = read_data #/self.counting_time  # convert to cts/s
        self.dte_signal.emit(DataToExport(name='Counts',
                                          data=[DataWithAxes(name='Counts', data=[np.array([data])],
                                                             source=DataSource['raw'],
                                                             dim='Data0D', labels=['Counts (Hz)'])]))

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        self.task.stop()
        self.close()
        self.emit_status(ThreadCommand('Update_Status', ['Acquisition stopped.']))
        return ''

    def update_tasks(self):
        """Set up the counting tasks in the NI card."""
        # Create channels

        self.counter_channel = Counter(name=self.settings.child("counter_channel").value(),
                                       source="Counter", edge=Edge.names()[0])
        #
        #self.controller["clock"].update_task(channels=[self.clock_channel],
        #                                     clock_settings=ClockSettings(),
        #                                     trigger_settings=TriggerSettings())
        #self.controller["clock"].task.CfgImplicitTiming(DAQmx_Val_ContSamps, 1)
        #
        #self.controller["counter"].update_task(channels=[self.counter_channel],
        #                                       clock_settings=ClockSettings(),
        #                                       trigger_settings=TriggerSettings())

        # connect the clock to the counter
        #self.controller["counter"].task.SetSampClkSrc("/" + self.clock_channel.name + "InternalOutput")


if __name__ == '__main__':
    main(__file__)
