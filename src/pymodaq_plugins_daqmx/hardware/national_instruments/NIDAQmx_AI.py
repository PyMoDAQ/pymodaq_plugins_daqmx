"""Base class of the thin analog input viewers (AI and DualAI) built on top of the NIDAQmx wrapper."""
import numpy as np

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters
from pymodaq.utils.data import DataFromPlugins, Axis
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq_data import DataToExport

from pymodaq_plugins_daqmx.hardware.national_instruments.daqmxni import (
    NIDAQmx, ClockSettings, AIChannel, ChannelType, UsageTypeAI, TerminalConfiguration)

logger = set_logger(get_module_name(__file__))

AI_CHANNELS = NIDAQmx.get_NIDAQ_channels(source_type=ChannelType.ANALOG_INPUT)


def default_channel(index: int) -> str:
    """The index-th analog input of the computer, the last one if there are fewer, '' if there is none."""
    if not AI_CHANNELS:
        return ''
    return AI_CHANNELS[min(index, len(AI_CHANNELS) - 1)]


class DAQ_Viewer_AIBase(DAQ_Viewer_base):
    """Acquire `Nsamples` points at `frequency` on one or several analog inputs, as 0D (mean) or 1D data.

    Subclasses declare in `params` one list parameter per channel and give their names in `channel_names`.
    """
    params = comon_parameters + [
        {'title': 'Display type:', 'name': 'display', 'type': 'list', 'limits': ['0D', '1D'],
         'value': '0D'},
        {'title': 'Frequency Acq.:', 'name': 'frequency', 'type': 'int', 'value': 1000, 'min': 1},
        {'title': 'Nsamples:', 'name': 'Nsamples', 'type': 'int', 'value': 100, 'default': 100, 'min': 1},
    ]
    hardware_averaging = True
    live_mode_available = True
    data_name = 'NI AI'

    def ini_attributes(self):
        self.controller: NIDAQmx = None
        self.channels_ai: list[AIChannel] = []
        self.live = False
        self.Naverage = 1

    def channel_names(self) -> list[str]:
        raise NotImplementedError

    def ini_detector(self, controller=None):
        if self.is_master:
            self.controller = NIDAQmx()
        else:
            self.controller = controller
        self.update_tasks()
        return 'Analog input ready', True

    def commit_settings(self, param):
        if self.controller is not None:
            self.update_tasks()

    def update_tasks(self):
        self.channels_ai = [AIChannel(name=name, source=ChannelType.ANALOG_INPUT,
                                      analog_type=UsageTypeAI.VOLTAGE, value_min=-10., value_max=10.,
                                      termination=TerminalConfiguration.DIFF)
                            for name in self.channel_names()]
        clock = ClockSettings(frequency=self.settings['frequency'], Nsamples=self.settings['Nsamples'],
                              repetition=False)
        self.controller.update_task(self.channels_ai, clock)

    def read_samples(self) -> np.ndarray:
        """Run one finite acquisition and return an array of shape (nchannels, Nsamples)."""
        nsamples = self.settings['Nsamples']
        timeout = nsamples / self.settings['frequency'] + 5.
        self.controller.task.start()
        try:
            raw = self.controller.task.read(number_of_samples_per_channel=nsamples, timeout=timeout)
        finally:
            self.controller.task.stop()
        data = np.asarray(raw, dtype=float)
        return data.reshape(len(self.channels_ai), nsamples)

    def grab_data(self, Naverage=1, **kwargs):
        if 'live' in kwargs:
            self.live = kwargs['live']
        self.Naverage = Naverage
        total = sum(self.read_samples() for _ in range(Naverage)) / Naverage
        self.emit_data(total)

    def emit_data(self, data: np.ndarray):
        display = self.settings['display']
        if display == '0D':
            data = data.mean(axis=1, keepdims=True)
            axes = []
        else:
            axes = [Axis('time', 's', data=np.arange(data.shape[1]) / self.settings['frequency'], index=0)]
        self.dte_signal.emit(DataToExport(self.data_name, data=[
            DataFromPlugins(name=self.data_name, data=[row for row in data], dim=f'Data{display}',
                            labels=[ch.name for ch in self.channels_ai], axes=axes)]))

    def stop(self):
        try:
            self.controller.stop()
        except Exception:
            logger.debug('The task could not be stopped', exc_info=True)

    def close(self):
        if self.is_master and self.controller is not None:
            self.controller.close()
