"""Base class of the thin analog input viewers (AI and DualAI) built on top of the NIDAQmx wrapper."""
from collections import deque

import numpy as np

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters
from pymodaq.utils.data import DataFromPlugins, Axis
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq_data import DataToExport

from nidaqmx.constants import TerminalConfiguration

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AIVoltage, AnalogInputTask, ChannelKind, ClockSettings, NIDAQSystem, TaskConfig)
from pymodaq_plugins_daqmx.hardware.national_instruments.qt_task_bridge import QtTaskBridge

logger = set_logger(get_module_name(__file__))

AI_CHANNELS = NIDAQSystem().all_channels(ChannelKind.AI)


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
    live_mode_available = True  # with live=True: one continuous task, one data per block of Nsamples
    data_name = 'NI AI'

    def ini_attributes(self):
        self.controller: AnalogInputTask = None  # one task for the channels and the clock of this plugin
        self.channel_labels: list[str] = []
        self.live = False
        self.Naverage = 1
        self._bridge = None  # QtTaskBridge of the continuous task, while streaming

    def channel_names(self) -> list[str]:
        raise NotImplementedError

    def ini_detector(self, controller=None):
        self.update_tasks()
        return 'Analog input ready', True

    def commit_settings(self, param):
        if self.controller is not None:
            self.update_tasks()

    def update_tasks(self, streaming=False):
        """Replace the task by one that follows the settings: finite for a snap, continuous for the live mode."""
        self.close()
        self.channel_labels = self.channel_names()
        channels = [AIVoltage(name, min_val=-10., max_val=10., terminal_config=TerminalConfiguration.DIFF)
                    for name in self.channel_labels]
        clock = ClockSettings(rate=self.settings['frequency'],
                              samples=None if streaming else self.settings['Nsamples'])
        self.controller = AnalogInputTask(TaskConfig(channels=channels, timing=clock))

    def read_samples(self) -> np.ndarray:
        """Run one finite acquisition and return an array of shape (nchannels, Nsamples)."""
        self.controller.start()
        try:
            return self.controller.read_analog()
        finally:
            self.controller.stop()

    def grab_data(self, Naverage=1, live=False, **kwargs):
        self.live = live
        self.Naverage = Naverage
        if live:
            self.start_live()
        else:
            total = sum(self.read_samples() for _ in range(Naverage)) / Naverage
            self.emit_data(total)

    def start_live(self):
        """Acquire continuously: each block of Nsamples is emitted as a data (mean of the last Naverage blocks)."""
        self.stop_live()
        self.update_tasks(streaming=True)  # a stopped task still reserves its channels: no snap task in parallel
        self._recent_blocks = deque(maxlen=self.Naverage)
        self._bridge = QtTaskBridge(self.controller)
        self._bridge.samples_ready.connect(self._emit_block)
        self.controller.start(notify_every=self.settings['Nsamples'])

    def stop_live(self):
        if self._bridge is not None:
            self._bridge.samples_ready.disconnect(self._emit_block)
            self._bridge = None
            self.update_tasks()  # back to the task of the snaps

    def _emit_block(self, block: np.ndarray):
        self._recent_blocks.append(block)
        self.emit_data(sum(self._recent_blocks) / len(self._recent_blocks))

    def emit_data(self, data: np.ndarray):
        display = self.settings['display']
        if display == '0D':
            data = data.mean(axis=1, keepdims=True)
            axes = []
        else:
            axes = [Axis('time', 's', data=np.arange(data.shape[1]) / self.settings['frequency'], index=0)]
        self.dte_signal.emit(DataToExport(self.data_name, data=[
            DataFromPlugins(name=self.data_name, data=[row for row in data], dim=f'Data{display}',
                            labels=self.channel_labels, axes=axes)]))

    def stop(self):
        try:
            self.controller.stop()
        except Exception:
            logger.debug('The task could not be stopped', exc_info=True)
        self.stop_live()

    def close(self):
        self._bridge = None
        if self.controller is not None:
            self.controller.close()
            self.controller = None
