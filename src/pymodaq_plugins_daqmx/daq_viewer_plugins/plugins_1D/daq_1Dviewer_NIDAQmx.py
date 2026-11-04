import numpy as np
from pymodaq_data import DataToExport
from pymodaq.utils.data import DataFromPlugins
from pymodaq_plugins_daqmx.hardware.national_instruments.NIDAQmx_Viewer import DAQ_NIDAQmx_Viewer
from pymodaq_plugins_daqmx.hardware.national_instruments.NIDAQmx_base import ChannelType
from pymodaq.utils.logger import set_logger, get_module_name
logger = set_logger(get_module_name(__file__))

class DAQ_1DViewer_NIDAQmx(DAQ_NIDAQmx_Viewer):
    """
    Plugin for bufferized 1D data visualization & acquisition with NI modules (plugged in NI cDAQ or NI-USB).
    """
    live_mode_available = True

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state, control_type='1D')

    def grab_data(self, Naverage=1, **kwargs):
        """
            | grab the current values with NIDAQ profile procedure.
            |
            | Send the data_grabed_signal once done.

            =============== ======== ===============================================
            **Parameters**  **Type**  **Description**
            *Naverage*      int       Number of values to average
            =============== ======== ===============================================
        """
        update = False

        if 'live' in kwargs:
            if kwargs['live'] != self.live:
                update = True
            self.live = kwargs['live']

        if Naverage != self.Naverage:
            self.Naverage = Naverage
            update = True
        if update:
            self.update_task()

        if self.controller.task is None:
            self.update_task()

        if self.settings['NIDAQ_type'] == ChannelType.ANALOG_INPUT.name:
            try:
                self.controller.register_callback(self.emit_data, "Nsamples", self.clock_settings.Nsamples)
            except AttributeError:
                logger.error("Can't find a task to run")
        elif self.settings['NIDAQ_type'] == ChannelType.COUNTER_INPUT.name:
            self.timer.start(self.settings['counter_settings', 'counting_time'])
        self.controller.start()

    def emit_data(self, task_handle, every_n_samples_event_type, number_of_samples, callback_data):
        channels_names = [ch.name for ch in self.channels]
        data_from_task = self.controller.task.read(self.settings['nsamplestoread'], timeout=20.0)
        if not len(self.controller.task.channels.channel_names) != 1:
            data_dfp = [np.array(data_from_task)]
        else:
            data_dfp = list(map(np.array, data_from_task))
        self.dte_signal.emit(DataToExport(name='NIDAQmx',
                                          data=[DataFromPlugins(name='Data from ' + self.controller.device.name,
                                                                data=data_dfp,
                                                                dim=f'Data{self.control_type}',
                                                                labels=channels_names,
                                                                ),
                                                ]))
        return 0  # mandatory for the NIDAQmx callback