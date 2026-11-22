"""Base class of the thin analog input viewers (AI and DualAI) built on top of the NIDAQmx wrapper."""
from typing import List, Optional, Tuple

import numpy as np

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters
from pymodaq.utils.data import DataFromPlugins, Axis
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq_data import DataToExport

from nidaqmx.constants import TerminalConfiguration
from pyqtgraph.parametertree import Parameter

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
    """Acquire points at `frequency` on one or several analog inputs, as 0D (mean) or 1D data.

    In 0D, the Naverage of the viewer is the number of points averaged by the acquisition (`Nsamples` is hidden).
    In 1D, `Nsamples` is the length of the trace and Naverage the number of traces averaged.

    Subclasses declare in `params` one list parameter per channel and give their names in `channel_names`.
    """
    params = comon_parameters + [
        {'title': 'Display type:', 'name': 'display', 'type': 'list', 'limits': ['0D', '1D'],
         'value': '0D'},
        {'title': 'Frequency Acq.:', 'name': 'frequency', 'type': 'int', 'value': 1000, 'min': 1},
        {'title': 'Nsamples:', 'name': 'Nsamples', 'type': 'int', 'value': 100, 'default': 100, 'min': 1},
    ]
    hardware_averaging = True
    live_mode_available = True  # with live=True: one continuous task, one data per block of samples
    data_name = 'NI AI'

    def ini_attributes(self):
        self.controller: Optional[AnalogInputTask] = None  # one task for the channels and the clock of this plugin
        self.channel_labels: List[str] = []
        self.live: bool = False
        self.Naverage: int = 1
        self._bridge: Optional[QtTaskBridge] = None  # relays the notifications of the continuous task, in live
        self._traces: List[np.ndarray] = []  # the blocks of the series being averaged in live 1D

    def channel_names(self) -> List[str]:
        raise NotImplementedError

    def channels(self) -> list:
        """The channels of the task, in the order of the data; by default analog voltages named by `channel_names`."""
        return [AIVoltage(name, min_val=-10., max_val=10., terminal_config=TerminalConfiguration.DIFF)
                for name in self.channel_names()]

    def ini_detector(self, controller: Optional[AnalogInputTask] = None) -> Tuple[str, bool]:
        self.settings.child('Nsamples').setOpts(visible=self.settings['display'] == '1D')
        if self.is_master:
            self.update_tasks()
        else:  # a slave uses the task of its master, which owns it: it neither replaces nor closes it
            self.controller = controller
            self.channel_labels = [channel.name for channel in self.channels()]
        return 'Analog input ready', True

    def commit_settings(self, param: Parameter) -> None:
        if param.name() == 'display':
            self.settings.child('Nsamples').setOpts(visible=param.value() == '1D')
        if self.controller is not None and self.is_master:
            self.update_tasks(streaming=self._bridge is not None)

    def samples_per_block(self) -> int:
        """Points of one acquisition: the averaging of the viewer in 0D, the length of the trace in 1D."""
        return self.Naverage if self.settings['display'] == '0D' else self.settings['Nsamples']

    def update_tasks(self, streaming: bool = False) -> None:
        """Replace the task by one that follows the settings: finite for a snap, continuous for the live mode."""
        self.close()
        channels = self.channels()
        self.channel_labels = [channel.name for channel in channels]
        clock = ClockSettings(rate=self.settings['frequency'],
                              samples=None if streaming else self.samples_per_block())
        self.controller = AnalogInputTask(TaskConfig(channels=channels, timing=clock))

    def read_samples(self) -> np.ndarray:
        """Run one finite acquisition and return an array of shape (nchannels, Nsamples)."""
        self.controller.start()
        try:
            return self.controller.read_analog()
        finally:
            self.controller.stop()

    def grab_data(self, Naverage: int = 1, live: bool = False, **kwargs) -> None:
        self.live = live
        self.Naverage = Naverage
        if live:
            self.start_live()
            return
        if (self.controller.config.timing.samples != self.samples_per_block()
                or list(self.controller.config.channels) != self.channels()):
            self.update_tasks()  # follow the Naverage of the viewer in 0D, and the channels added or changed
        if self.settings['display'] == '0D':
            self.emit_points(self.read_samples())
        else:
            self.emit_traces([self.read_samples() for _ in range(Naverage)])

    def start_live(self) -> None:
        """Acquire continuously: 0D, one data per block of Naverage points; 1D, one data per Naverage traces."""
        self.stop_live()
        self.update_tasks(streaming=True)  # a stopped task still reserves its channels: no snap task in parallel
        self._traces = []
        self._bridge = QtTaskBridge(self.controller)
        self._bridge.samples_ready.connect(self._on_block)
        self.controller.start(notify_every=self.samples_per_block())

    def stop_live(self) -> None:
        if self._bridge is not None:
            self._bridge.samples_ready.disconnect(self._on_block)
            self._bridge.close()  # before the task is closed (by update_tasks)
            self._bridge = None
            self.update_tasks()  # back to the task of the snaps

    def _on_block(self, block: np.ndarray) -> None:
        if self.settings['display'] == '0D':
            self.emit_points(block)
            return
        self._traces.append(block)
        if len(self._traces) >= self.Naverage:  # the traces are averaged, emitted, then a new series starts
            traces, self._traces = self._traces, []
            self.emit_traces(traces)

    def emit_points(self, block: np.ndarray) -> None:
        """0D data: the mean of the points of the block (channels, points), with its standard error."""
        points = DataFromPlugins(name=self.data_name, data=[row for row in block], dim='Data1D',
                                 labels=self.channel_labels)
        self.dte_signal.emit(DataToExport(self.data_name, data=[points.mean_with_errors(axis=0)]))

    def emit_traces(self, traces: List[np.ndarray]) -> None:
        """1D data: the mean of the traces (each shaped (channels, points)), with its standard error."""
        times = np.arange(traces[0].shape[1]) / self.settings['frequency']
        if len(traces) == 1:  # nothing to average, so no error either
            data = DataFromPlugins(name=self.data_name, data=[row for row in traces[0]], dim='Data1D',
                                   labels=self.channel_labels, axes=[Axis('time', 's', data=times, index=0)])
            self.dte_signal.emit(DataToExport(self.data_name, data=[data]))
            return
        stack = np.stack(traces)  # (traces, channels, points): the traces are the first, navigation, axis
        acquisitions = Axis('acquisition', data=np.arange(float(len(traces))), index=0)
        data = DataFromPlugins(name=self.data_name, data=[stack[:, ch, :] for ch in range(stack.shape[1])],
                               dim='DataND', nav_indexes=(0,), labels=self.channel_labels,
                               axes=[acquisitions, Axis('time', 's', data=times, index=1)])
        self.dte_signal.emit(DataToExport(self.data_name, data=[data.mean_with_errors(axis=0)]))

    def stop(self) -> None:
        try:
            self.controller.stop()
        except Exception:
            logger.debug('The task could not be stopped', exc_info=True)
        self.stop_live()

    def close(self) -> None:
        if self._bridge is not None:
            self._bridge.close()
            self._bridge = None
        if self.controller is not None and self.is_master:
            self.controller.close()
            self.controller = None
