import numpy as np

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.data import DataFromPlugins
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq_data import DataToExport

from pymodaq_plugins_daqmx.hardware.national_instruments.daqmxni import (
    NIDAQmx, CIChannel, ClockCounter, ClockSettings, ChannelType, UsageTypeCI, Edge, AcquisitionType)

logger = set_logger(get_module_name(__file__))

COUNTER_CHANNELS = NIDAQmx.get_NIDAQ_channels(source_type=ChannelType.COUNTER_INPUT)


def _channel(index: int) -> str:
    return COUNTER_CHANNELS[min(index, len(COUNTER_CHANNELS) - 1)] if COUNTER_CHANNELS else ''


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
        self.controller: dict[str, NIDAQmx] = None  # one wrapper (hence one task) for the clock and one for the counter

    @property
    def counting_time(self) -> float:
        return 1 / self.settings['clock_freq']

    def ini_detector(self, controller=None):
        self.controller = {'clock': NIDAQmx(), 'counter': NIDAQmx()}
        self.update_tasks()
        self.dte_signal_temp.emit(self._dte(0.))
        return 'NI counter ready', True

    def commit_settings(self, param):
        self.stop()
        self.update_tasks()

    def update_tasks(self):
        """Create the clock task and the edge counting task, the latter being timed by the former."""
        clock_channel = ClockCounter(clock_frequency=self.settings['clock_freq'], name=self.settings['clock_channel'])
        counter_channel = CIChannel(name=self.settings['counter_channel'], source=ChannelType.COUNTER_INPUT,
                                    counter_type=UsageTypeCI.COUNT_EDGES, edge=Edge.RISING)
        clock = self.controller['clock']
        clock.update_task([clock_channel], ClockSettings(Nsamples=1))
        clock.task.timing.cfg_implicit_timing(sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=1)

        counter = self.controller['counter']
        counter.update_task([counter_channel], ClockSettings(Nsamples=1))
        # one sample is taken at the first tick of the clock: the number of edges during one counting time
        counter.task.timing.cfg_samp_clk_timing(self.settings['clock_freq'],
                                                source='/' + clock_channel.name + 'InternalOutput',
                                                sample_mode=AcquisitionType.FINITE, samps_per_chan=1)

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
        counter, clock = self.controller['counter'], self.controller['clock']
        counter.task.start()  # armed first: it waits for the clock
        clock.task.start()
        try:
            return int(counter.task.read(number_of_samples_per_channel=1, timeout=2 * self.counting_time + 1.))
        finally:
            clock.stop()
            counter.stop()

    def stop(self):
        if self.controller is not None:
            for ctrl in self.controller.values():
                try:
                    ctrl.stop()
                except Exception:
                    logger.debug('The task could not be stopped', exc_info=True)
        self.emit_status(ThreadCommand('Update_Status', ['Acquisition stopped.']))

    def close(self):
        if self.controller is not None:
            for ctrl in self.controller.values():
                ctrl.close()


if __name__ == '__main__':
    main(__file__)
