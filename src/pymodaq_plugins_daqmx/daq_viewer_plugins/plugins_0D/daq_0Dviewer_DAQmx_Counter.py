from dataclasses import dataclass

import numpy as np

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.data import DataFromPlugins
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq_data import DataToExport

from nidaqmx.constants import Edge

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    CICountEdges, COPulseFreq, ChannelKind, ClockSettings, CounterInputTask, CounterOutputTask, ImplicitTiming, NIDAQSystem,
    TaskConfig, counter_output_terminal)

logger = set_logger(get_module_name(__file__))

COUNTER_CHANNELS = NIDAQSystem().all_channels(ChannelKind.CI)


def _channel(index: int) -> str:
    return COUNTER_CHANNELS[min(index, len(COUNTER_CHANNELS) - 1)] if COUNTER_CHANNELS else ''


@dataclass
class CounterControllers:
    """The two tasks of the plugin: the clock sets the counting time, the counter counts edges during it."""
    clock: CounterOutputTask
    counter: CounterInputTask

    def __iter__(self):
        return iter((self.clock, self.counter))


class DAQ_0DViewer_DAQmx_Counter(DAQ_Viewer_base):
    """Rate of the edges (pulses, photons...) received on the input of a NI counter, in counts per second.

    A second counter, used as a clock, defines the counting time (1 / clock frequency): the edge counter is read
    once at each tick of that clock.
    """
    params = comon_parameters + [
        {'title': 'Counting channel:', 'name': 'counter_channel', 'type': 'list', 'limits': COUNTER_CHANNELS,
         'value': _channel(0)},
        {'title': 'Clock channel:', 'name': 'clock_channel', 'type': 'list', 'limits': COUNTER_CHANNELS,
         'value': _channel(1)},
        {'title': 'Clock frequency (Hz):', 'name': 'clock_freq', 'type': 'float', 'value': 100., 'default': 100.,
         'min': 1},
    ]

    def ini_attributes(self):
        self.controller = None  # CounterControllers

    @property
    def counting_time(self) -> float:
        return 1 / self.settings['clock_freq']

    def ini_detector(self, controller=None):
        self.update_tasks()
        self.dte_signal_temp.emit(self._dte(0.))
        return 'NI counter ready', True

    def commit_settings(self, param):
        self.update_tasks()

    def update_tasks(self):
        """Create the clock task and the edge counting task, the latter being timed by the former."""
        self.close()
        clock_channel = self.settings['clock_channel']
        frequency = self.settings['clock_freq']
        clock = CounterOutputTask(TaskConfig(channels=[COPulseFreq(clock_channel, frequency=frequency)],
                                             timing=ImplicitTiming()))
        # one sample is taken at the first tick of the clock: the number of edges during one counting time
        counter = CounterInputTask(TaskConfig(
            channels=[CICountEdges(self.settings['counter_channel'], edge=Edge.RISING)],
            timing=ClockSettings(rate=frequency, samples=1, source=counter_output_terminal(clock_channel))))
        self.controller = CounterControllers(clock, counter)

    def _dte(self, rate: float) -> DataToExport:
        return DataToExport('Counter', data=[DataFromPlugins(
            name='Counter', data=[np.array([rate])], dim='Data0D', labels=['Count rate'], units='counts/s')])

    def grab_data(self, Naverage=1, **kwargs):
        counts = 0
        for _ in range(Naverage):
            counts += self.count_once()
        self.dte_signal.emit(self._dte(counts / Naverage / self.counting_time))

    def count_once(self) -> int:
        """Number of edges during one counting time."""
        counter, clock = self.controller.counter, self.controller.clock
        counter.start()  # armed first: it waits for the clock
        clock.start()
        try:
            return int(counter.read_counter(samples=1)[0, 0])
        finally:
            clock.stop()
            counter.stop()

    def stop(self):
        if self.controller is not None:
            for ctrl in self.controller:
                try:
                    ctrl.stop()
                except Exception:
                    logger.debug('The task could not be stopped', exc_info=True)
        self.emit_status(ThreadCommand('Update_Status', ['Acquisition stopped.']))

    def close(self):
        if self.controller is not None:
            for ctrl in self.controller:
                ctrl.close()
            self.controller = None


if __name__ == '__main__':
    main(__file__)
