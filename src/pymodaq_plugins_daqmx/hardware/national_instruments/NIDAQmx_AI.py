"""Base class of the thin analog input viewers (AI and DualAI) built on top of the NIDAQmx wrapper."""
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
        self.controller: AnalogInputTask = None  # one task for the channels and the clock of this plugin
        self.channel_labels: list[str] = []
        self.live = False
        self.Naverage = 1
        self._bridge = None  # QtTaskBridge of the continuous task, while streaming

    def channel_names(self) -> list[str]:
        raise NotImplementedError

    def ini_detector(self, controller=None):
        self.settings.child('Nsamples').setOpts(visible=self.settings['display'] == '1D')
        self.update_tasks()
        return 'Analog input ready', True

    def commit_settings(self, param):
        if param.name() == 'display':
            self.settings.child('Nsamples').setOpts(visible=param.value() == '1D')
        if self.controller is not None:
            self.update_tasks(streaming=self._bridge is not None)

    def samples_per_block(self) -> int:
        """Points of one acquisition: the averaging of the viewer in 0D, the length of the trace in 1D."""
        return self.Naverage if self.settings['display'] == '0D' else self.settings['Nsamples']

    def update_tasks(self, streaming=False):
        """Replace the task by one that follows the settings: finite for a snap, continuous for the live mode."""
        self.close()
        self.channel_labels = self.channel_names()
        channels = [AIVoltage(name, min_val=-10., max_val=10., terminal_config=TerminalConfiguration.DIFF)
                    for name in self.channel_labels]
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

    def grab_data(self, Naverage=1, live=False, **kwargs):
        self.live = live
        self.Naverage = Naverage
        if live:
            self.start_live()
            return
        if self.controller.config.timing.samples != self.samples_per_block():
            self.update_tasks()  # the 0D acquisition follows the Naverage of the viewer
        if self.settings['display'] == '0D':
            self.emit_points(self.read_samples())
        else:
            self.emit_traces([self.read_samples() for _ in range(Naverage)])

    def start_live(self):
        """Acquire continuously: 0D, one data per block of Naverage points; 1D, one data per Naverage traces."""
        self.stop_live()
        self.update_tasks(streaming=True)  # a stopped task still reserves its channels: no snap task in parallel
        self._traces = []
        self._bridge = QtTaskBridge(self.controller)
        self._bridge.samples_ready.connect(self._on_block)
        self.controller.start(notify_every=self.samples_per_block())

    def stop_live(self):
        if self._bridge is not None:
            self._bridge.samples_ready.disconnect(self._on_block)
            self._bridge.close()  # before the task is closed (by update_tasks)
            self._bridge = None
            self.update_tasks()  # back to the task of the snaps

    def _on_block(self, block: np.ndarray):
        if self.settings['display'] == '0D':
            self.emit_points(block)
            return
        self._traces.append(block)
        if len(self._traces) >= self.Naverage:  # the traces are averaged, emitted, then a new series starts
            traces, self._traces = self._traces, []
            self.emit_traces(traces)

    @staticmethod
    def _standard_error(values: np.ndarray, axis: int, keepdims: bool = False):
        """Standard error of the mean along ``axis``; None if there is a single value."""
        n = values.shape[axis]
        return values.std(axis=axis, ddof=1, keepdims=keepdims) / np.sqrt(n) if n > 1 else None

    def emit_points(self, block: np.ndarray):
        """0D data: the mean of the points of the block (channels, points), with its standard error."""
        self.emit_data(block.mean(axis=1, keepdims=True), self._standard_error(block, axis=1, keepdims=True))

    def emit_traces(self, traces: list):
        """1D data: the mean of the traces (each shaped (channels, points)), with its standard error."""
        stack = np.stack(traces)
        self.emit_data(stack.mean(axis=0), self._standard_error(stack, axis=0))

    def emit_data(self, data: np.ndarray, errors: np.ndarray = None):
        display = self.settings['display']
        if display == '0D':
            axes = []
        else:
            axes = [Axis('time', 's', data=np.arange(data.shape[1]) / self.settings['frequency'], index=0)]
        self.dte_signal.emit(DataToExport(self.data_name, data=[
            DataFromPlugins(name=self.data_name, data=[row for row in data], dim=f'Data{display}',
                            labels=self.channel_labels, axes=axes,
                            errors=None if errors is None else [row for row in errors])]))

    def stop(self):
        try:
            self.controller.stop()
        except Exception:
            logger.debug('The task could not be stopped', exc_info=True)
        self.stop_live()

    def close(self):
        if self._bridge is not None:
            self._bridge.close()
            self._bridge = None
        if self.controller is not None:
            self.controller.close()
            self.controller = None
