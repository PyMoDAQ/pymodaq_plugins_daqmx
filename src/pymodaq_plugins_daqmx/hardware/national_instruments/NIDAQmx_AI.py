"""Base class of the analog input viewers, built on the ``nidaqmx`` API of this package.

Overview:

* ``Acquisition`` describes what one task acquires (a module: channels, frequency, clock, start trigger);
* ``start_order`` and ``trace_axis`` are the two rules that depend on the clocks (which task starts first, what the
  axis of a trace is);
* ``DAQ_Viewer_AIBase`` builds one task for each acquisition (``update_tasks``), grabs finite blocks (``grab_data``)
  or streams them in live mode (``start_live``), and emits the data (``emit_points``, ``emit_traces``). Subclasses
  only tell *what* to acquire by overriding ``channels`` or ``acquisitions``.
"""
from typing import List, Optional, Tuple

from dataclasses import dataclass
from functools import partial

import numpy as np

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters
from pymodaq.utils.data import DataFromPlugins, Axis
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq_data import DataToExport

from nidaqmx.constants import TerminalConfiguration
from pyqtgraph.parametertree import Parameter

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AIVoltage, AnalogInputTask, ChannelKind, ClockSettings, NIDAQSystem, TaskConfig, TaskGroup)
from pymodaq_plugins_daqmx.hardware.national_instruments.qt_task_bridge import QtTaskBridge

logger = set_logger(get_module_name(__file__))

MIN_CLOCKED_SAMPLES = 2
AI_CHANNELS = NIDAQSystem().all_channels(ChannelKind.AI)


def default_channel(index: int) -> str:
    """The index-th analog input of the computer, the last one if there are fewer, '' if there is none."""
    if not AI_CHANNELS:
        return ''
    return AI_CHANNELS[min(index, len(AI_CHANNELS) - 1)]


@dataclass(frozen=True)
class Acquisition:
    """What one task acquires: its channels at its frequency, and a data of its own named after ``name`` (the module)."""
    name: str
    channels: list
    frequency: int
    unread: tuple = ()  # names of the channels that are in the task but not in the data
    clock: str = ''  # terminal of the sample clock, empty for the onboard clock of the module
    trigger: Optional[object] = None  # what starts the task (a trigger of the API), None to start it at once
    waits_for: tuple = ()  # the other modules whose signals the task waits for (their clock, their trigger...)

    @property
    def rows(self) -> List[int]:
        """The rows of the acquired block that go in the data."""
        return [i for i, channel in enumerate(self.channels) if channel.name not in self.unread]

    @property
    def labels(self) -> List[str]:
        """The names of the channels of the data."""
        return [self.channels[i].name for i in self.rows]


def trace_axis(acquisition: 'Acquisition', points: int, index: int) -> Axis:
    """The axis along a trace: time in seconds, or the number of the sample if the clock is external, as the rate that
    is given to the driver is then only the highest the clock may have, so a time computed with it could be false."""
    if acquisition.clock:
        return Axis('sample', '', data=np.arange(points, dtype=float), index=index)
    return Axis('time', 's', data=np.arange(points) / acquisition.frequency, index=index)


def start_order(acquisitions: List['Acquisition']) -> List[int]:
    """The order in which to start the tasks: a task that waits for a signal of another module (its clock, its
    trigger) is armed before the module that gives it. A loop of such waits is a ``ValueError`` naming the modules."""
    names = [a.name for a in acquisitions]
    pending = list(range(len(acquisitions)))
    order = []
    while pending:
        # a task can start once no pending task waits for it
        ready = [i for i in pending if not any(names[i] in acquisitions[j].waits_for for j in pending if j != i)]
        if not ready:
            raise ValueError('The modules ' + ', '.join(names[i] for i in pending) + ' wait for each other\'s signals '
                             '(clock or trigger): one of them has to use its own clock')
        order.append(ready[0])
        pending.remove(ready[0])
    return order


class DAQ_Viewer_AIBase(DAQ_Viewer_base):
    """Acquire points at `frequency` on one or several analog inputs, as 0D (mean) or 1D data.

    In 0D, the Naverage of the viewer is the number of points averaged by the acquisition (`Nsamples` is hidden).
    In 1D, `Nsamples` is the length of the trace and Naverage the number of traces averaged.

    Subclasses give the channels (`channels`, or `channel_names` for voltages) or, to acquire with several tasks, the
    list of `acquisitions`. Each acquisition has its task and gives its own data, so the tasks can differ in
    frequency, clock and start trigger.
    """
    params = comon_parameters + [
        {'title': 'Display type:', 'name': 'display', 'type': 'list', 'limits': ['0D', '1D'],
         'value': '0D'},
        {'title': 'Frequency Acq.:', 'name': 'frequency', 'type': 'int', 'value': 1000, 'min': 1},
        {'title': 'Nsamples:', 'name': 'Nsamples', 'type': 'int', 'value': 100, 'default': 100, 'min': 2},
    ]
    hardware_averaging = True
    live_mode_available = True  # with live=True: one continuous task, one data per block of samples
    data_name = 'NI AI'

    def ini_attributes(self):
        self.controller = None  # the task of this plugin, or the group of its tasks when it has several
        self.tasks: List[AnalogInputTask] = []  # one per acquisition
        self.start_order: List[int] = []  # the indexes of the tasks in the order they start
        self.acquisitions_done: List[Acquisition] = []  # what each task acquires, in the order of the tasks
        self._signature = None  # what the tasks were built for, to rebuild them when the settings changed
        self.live: bool = False
        self.Naverage: int = 1
        self._bridges: List[QtTaskBridge] = []  # relay the notifications of the continuous tasks, in live
        self._traces: List[List[np.ndarray]] = []  # for each task, the blocks of the series being averaged in live 1D

    @property
    def channel_labels(self) -> List[str]:
        return [label for acquisition in self.acquisitions_done for label in acquisition.labels]

    def channel_names(self) -> List[str]:
        raise NotImplementedError

    def channels(self) -> list:
        """The channels of the plugin, in the order of the data; by default analog voltages named by
        `channel_names`."""
        return [AIVoltage(name, min_val=-10., max_val=10., terminal_config=TerminalConfiguration.DIFF)
                for name in self.channel_names()]

    def acquisitions(self) -> List[Acquisition]:
        """What the tasks acquire, one data each: by default a single task for all the channels, at `frequency`."""
        channels = self.channels()
        return [Acquisition('', channels, self.settings['frequency'])] if channels else []

    def data_names(self, acquisitions: List[Acquisition]) -> List[str]:
        return [f'{self.data_name} {a.name}' if a.name else self.data_name for a in acquisitions]

    def ini_detector(self, controller=None) -> Tuple[str, bool]:
        self.settings.child('Nsamples').setOpts(visible=self.settings['display'] == '1D')
        if self.is_master:
            self.update_tasks()
        else:  # a slave uses the task of its master, which owns it: it neither replaces nor closes it
            self.controller = controller
            self.tasks = [controller]
            self.start_order = [0]
            self.acquisitions_done = [Acquisition('', self.channels(), self.settings['frequency'])]
            self._signature = self.signature()
        return 'Analog input ready', True

    def commit_settings(self, param: Parameter) -> None:
        if param.name() == 'display':
            self.settings.child('Nsamples').setOpts(visible=param.value() == '1D')
        if self.controller is not None and self.is_master:
            self.update_tasks(streaming=bool(self._bridges))

    def samples_per_block(self) -> int:
        """Points of one acquisition: the averaging of the viewer in 0D, the length of the trace in 1D."""
        return self.Naverage if self.settings['display'] == '0D' else self.settings['Nsamples']

    def task_samples(self) -> int:
        """Samples requested by a finite task: at least 2, the least that the driver accepts with a sample clock."""
        return max(self.samples_per_block(), MIN_CLOCKED_SAMPLES)

    def signature(self, streaming: bool = False):
        """What the tasks are built for: the acquisitions (channels, frequency, clock, trigger) and the samples of
        finite tasks. When it differs from the one the tasks were built with, the tasks are rebuilt at the next grab."""
        samples = None if streaming else self.task_samples()
        return tuple(self.acquisitions()), samples

    def update_tasks(self, streaming: bool = False) -> None:
        """Replace the tasks by ones that follow the settings: finite for a snap, continuous for the live mode.

        All tasks are built, or none is: a failure closes those already built (a task keeps its channels reserved).
        """
        self.close()
        acquisitions = self.acquisitions()
        if not acquisitions:  # a task needs a channel: they are built when the first one is added
            return
        samples = None if streaming else self.task_samples()
        order = start_order(acquisitions)  # before the tasks: a loop of waits must not leave tasks open
        tasks = []
        try:
            for acquisition in acquisitions:
                clock = ClockSettings(rate=acquisition.frequency, samples=samples, source=acquisition.clock)
                tasks.append(AnalogInputTask(TaskConfig(channels=acquisition.channels, timing=clock,
                                                        trigger=acquisition.trigger)))
        except Exception:
            for task in reversed(tasks):
                task.close()
            raise
        self.tasks, self.acquisitions_done = tasks, acquisitions
        self.start_order = order
        self.controller = tasks[0] if len(tasks) == 1 else TaskGroup(*tasks)
        self._signature = self.signature(streaming)

    def no_channel_message(self) -> None:
        self.emit_status(ThreadCommand('Update_Status', ['No channel to acquire: add one to the channels', 'log']))

    def ordered_tasks(self) -> List[AnalogInputTask]:
        """The tasks in the order they start: the ones that wait for the signal of another module come first."""
        return [self.tasks[i] for i in self.start_order]

    def read_samples(self) -> List[np.ndarray]:
        """Run one finite acquisition of each task, together, and return their arrays (nchannels, Nsamples), in the
        order of the tasks. The tasks start in `start_order` (those that wait for a signal first) and are stopped
        whatever happens, so that their channels are free for the next acquisition."""
        started = []
        try:
            for task in self.ordered_tasks():
                task.start()
                started.append(task)
            return [task.read_analog() for task in self.tasks]
        finally:
            for task in reversed(started):
                task.stop()

    def grab_data(self, Naverage: int = 1, live: bool = False, **kwargs) -> None:
        self.live = live
        self.Naverage = Naverage
        if live:
            self.start_live()
            return
        if self.controller is None or self._signature != self.signature():
            self.update_tasks()  # follow the Naverage of the viewer in 0D, and the channels added or changed
        if self.controller is None:
            self.no_channel_message()
            return
        if self.settings['display'] == '0D':
            # the surplus sample of Naverage=1 is dropped
            self.emit_points([block[:, :self.Naverage] for block in self.read_samples()])
        else:
            series = [self.read_samples() for _ in range(Naverage)]  # for each series, a block per task
            self.emit_traces([[blocks[i] for blocks in series] for i in range(len(self.tasks))])

    def start_live(self) -> None:
        """Acquire continuously: 0D, one data per block of Naverage points; 1D, one data per Naverage traces."""
        self.stop_live()
        self.update_tasks(streaming=True)  # a stopped task still reserves its channels: no snap task in parallel
        if self.controller is None:
            self.no_channel_message()
            return
        self._traces = [[] for _ in self.tasks]
        for index, task in enumerate(self.tasks):
            bridge = QtTaskBridge(task)
            bridge.samples_ready.connect(partial(self._on_block, index))
            self._bridges.append(bridge)
        started = []
        try:
            for task in self.ordered_tasks():
                task.start(notify_every=self.samples_per_block())
                started.append(task)
        except Exception:
            for task in reversed(started):
                task.stop()
            raise

    def stop_live(self) -> None:
        if self._bridges:
            for bridge in self._bridges:
                bridge.close()  # before the tasks are closed (by update_tasks)
            self._bridges = []
            self.update_tasks()  # back to the tasks of the snaps

    def _on_block(self, index: int, block: np.ndarray) -> None:
        """A block of samples of the task ``index`` arrived in live mode: emit it (0D), or add it to the series of
        traces being averaged and emit the mean when the series is complete (1D)."""
        if self.settings['display'] == '0D':
            self.emit_points([block], [index])
            return
        self._traces[index].append(block)
        if len(self._traces[index]) >= self.Naverage:  # the traces are averaged, emitted, then a new series starts
            traces, self._traces[index] = self._traces[index], []
            self.emit_traces([traces], [index])

    def emit_points(self, blocks: List[np.ndarray], indexes: Optional[List[int]] = None) -> None:
        """0D data: for each block (channels, points) of the tasks ``indexes``, the mean of its points with its
        standard error."""
        indexes = list(range(len(blocks))) if indexes is None else indexes
        names = self.data_names(self.acquisitions_done)
        data = []
        for index, block in zip(indexes, blocks):
            acquisition = self.acquisitions_done[index]
            if not acquisition.rows:  # nothing of this task is read: it only serves as a trigger
                continue
            points = DataFromPlugins(name=names[index], data=[block[i] for i in acquisition.rows], dim='Data1D',
                                     labels=acquisition.labels)
            data.append(points.mean_with_errors(axis=0))
        self.dte_signal.emit(DataToExport(self.data_name, data=data))

    def emit_traces(self, traces: List[List[np.ndarray]], indexes: Optional[List[int]] = None) -> None:
        """1D data: for each task of ``indexes``, the mean of its traces (each shaped (channels, points)), with its
        standard error."""
        indexes = list(range(len(traces))) if indexes is None else indexes
        names = self.data_names(self.acquisitions_done)
        data = []
        for index, series in zip(indexes, traces):
            acquisition = self.acquisitions_done[index]
            if not acquisition.rows:
                continue
            series = [trace[acquisition.rows] for trace in series]  # the channels that are read
            points = series[0].shape[1]
            if len(series) == 1:  # nothing to average, so no error either
                data.append(DataFromPlugins(name=names[index], data=[row for row in series[0]], dim='Data1D',
                                            labels=acquisition.labels,
                                            axes=[trace_axis(acquisition, points, 0)]))
                continue
            stack = np.stack(series)  # (traces, channels, points): the traces are the first, navigation, axis
            acquisitions = Axis('acquisition', data=np.arange(float(len(series))), index=0)
            averaged = DataFromPlugins(name=names[index], data=[stack[:, ch, :] for ch in range(stack.shape[1])],
                                       dim='DataND', nav_indexes=(0,), labels=acquisition.labels,
                                       axes=[acquisitions, trace_axis(acquisition, points, 1)])
            data.append(averaged.mean_with_errors(axis=0))
        self.dte_signal.emit(DataToExport(self.data_name, data=data))

    def stop(self) -> None:
        try:
            self.controller.stop()
        except Exception:
            logger.debug('The task could not be stopped', exc_info=True)
        self.stop_live()

    def close(self) -> None:
        for bridge in self._bridges:
            bridge.close()
        self._bridges = []
        if self.controller is not None and self.is_master:
            self.controller.close()
            self.controller = None
            self.tasks = []
