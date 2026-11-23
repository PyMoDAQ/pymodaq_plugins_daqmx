"""Several analog outputs of a NI device playing waveforms (arrays of samples), from one task with one clock.

The position of the actuator is a ``DataActuator`` holding one array of samples (volts) per chosen output, all of the
same length. The sample rate, the mode (finite, repeated, continuous) and the repetitions are the ``Waveform output``
settings of the plugin, which also lists what the device can do (``Waveform capabilities``): they follow the contract
of ``pymodaq_plugins_utils.hardware.waveform_output``, so the applications that design waveforms (the Dashboard
extension of ``pymodaq_plugins_waveform``) can send to this actuator and check what they send.

The move is done once the generation has started. The end of a finite or repeated generation is announced with the
status command ``generation_done`` (its value is the status of the driver, 0 if all went well). A new waveform replaces
the one being played with a break: the outputs go through 0 V in between (``live_update`` is False). The outputs are at
0 V at the start, after ``stop`` and at the close.
"""
import numpy as np
from nidaqmx.constants import Edge
from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, DataActuator, DataActuatorType,
                                                          comon_parameters_fun, main)
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq_data import Q_
from pymodaq_plugins_utils.hardware.waveform_output import (CAPABILITIES_NAME, OUTPUT_NAME, OutputMode,
                                                            WaveformOutput, fill_waveform_output_settings,
                                                            waveform_output_params)

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AOVoltage, ChannelKind, DigitalEdgeTrigger, NIDAQSystem)
from pymodaq_plugins_daqmx.hardware.national_instruments.waveform_player import WaveformPlayer

NO_TRIGGER = 'none'
EDGES = {'rising': Edge.RISING, 'falling': Edge.FALLING}


class DAQ_Move_NIDAQmx_Waveform(DAQ_Move_base):
    """Analog outputs of one NI device that play waveforms, started on demand or on a trigger."""
    is_multiaxes = False
    _axis_names = ['waveform']
    _controller_units = 'V'
    _epsilons = [1e-3]
    data_actuator_type = DataActuatorType.DataActuator
    has_encoder = False  # an output cannot be read back: the move is done once the samples are playing
    rebuild_on = ('channels', 'min_val', 'max_val', 'max_samples', 'trigger', 'trigger_edge')
    params = [
        {'title': 'Outputs:', 'name': 'channels', 'type': 'itemselect', 'checkbox': True,
         'value': dict(all_items=[], selected=[]),
         'tip': 'Analog outputs played together, all of the same device. The waveforms are given in this order'},
        {'title': 'Min:', 'name': 'min_val', 'type': 'float', 'value': -10., 'suffix': 'V',
         'tip': 'Lowest voltage of the outputs'},
        {'title': 'Max:', 'name': 'max_val', 'type': 'float', 'value': 10., 'suffix': 'V'},
        {'title': 'Sample clock:', 'name': 'clock_source', 'type': 'str', 'value': '',
         'tip': 'Terminal of an external sample clock such as /Dev1/PFI1. Empty: the clock of the device'},
        {'title': 'Start trigger:', 'name': 'trigger', 'type': 'list', 'limits': [NO_TRIGGER], 'value': NO_TRIGGER,
         'tip': 'Terminal whose edge starts the generation, or none to start it at once'},
        {'title': 'Trigger edge:', 'name': 'trigger_edge', 'type': 'list', 'limits': list(EDGES),
         'value': 'rising'},
        {'title': 'Max samples:', 'name': 'max_samples', 'type': 'int', 'value': 1000000, 'min': 2,
         'tip': 'Samples per output accepted by the actuator: a limit of the plugin to protect the memory, '
                'not a figure of the device'},
    ] + waveform_output_params() + comon_parameters_fun(False, axis_names=_axis_names, epsilon=_epsilons)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings.child('channels').setValue(dict(all_items=NIDAQSystem().all_channels(ChannelKind.AO),
                                                      selected=[]))

    def ini_attributes(self):
        self.controller: WaveformPlayer = None
        self.last_samples = None  # what was sent last, as the position

    # --- settings ----------------------------------------------------------------------------------------------

    @property
    def channel_names(self) -> list:
        return list(self.settings['channels']['selected'])

    def _device_limits(self, device: str) -> tuple:
        """The range of voltages, and the lowest and highest rates that the outputs of the device can do"""
        system = NIDAQSystem()
        ranges = system.ao_voltage_ranges(device)
        low = min((r[0] for r in ranges), default=self.settings['min_val'])
        high = max((r[1] for r in ranges), default=self.settings['max_val'])
        return low, high, system.ao_min_rate(device) or 0., system.ao_max_rate(device) or 0.

    def _fill_capabilities(self, device: str) -> None:
        system = NIDAQSystem()
        low, high, min_rate, max_rate = self._device_limits(device)
        triggers = [t for t in system.terminals(device) if 'PFI' in t] \
            if system.supports_start_trigger(device, ChannelKind.AO) else []
        self.settings.child('trigger').setLimits([NO_TRIGGER] + triggers)
        fill_waveform_output_settings(
            self.settings, n_channels=len(self.channel_names), min_rate=min_rate, max_rate=max_rate,
            max_samples=self.settings['max_samples'], min_voltage=max(low, self.settings['min_val']),
            max_voltage=min(high, self.settings['max_val']),
            modes=[OutputMode.FINITE, OutputMode.REPEAT, OutputMode.CONTINUOUS], triggers=triggers,
            live_update=False)

    def _make_player(self) -> WaveformPlayer:
        channels = [AOVoltage(name, self.settings['min_val'], self.settings['max_val'])
                    for name in self.channel_names]
        player = WaveformPlayer(channels)  # refuses no output and outputs of several devices
        self._fill_capabilities(channels[0].name.partition('/')[0])
        player.park()
        self.last_samples = [np.zeros(1) for _ in channels]
        return player

    # --- the actuator ------------------------------------------------------------------------------------------

    def ini_stage(self, controller=None):
        self.controller = self._make_player()
        return 'NI waveform output ready', True

    def close(self):
        if self.controller is not None:
            self.controller.close()
            self.controller = None

    def commit_settings(self, param):
        if param.name() in self.rebuild_on and self.controller is not None:
            self.controller.close()
            self.controller = self._make_player()

    def get_actuator_value(self) -> DataActuator:
        return DataActuator(data=[np.array(channel) for channel in self.last_samples], units='V')

    def _volts(self, value: DataActuator) -> np.ndarray:
        """The samples of a position in volts, one row per output"""
        factor = Q_(1, value.units).m_as('V') if value.units else 1.
        return np.array([np.asarray(channel, dtype=float) * factor for channel in value.data])

    def move_abs(self, value: DataActuator):
        try:
            samples = self._volts(value)
            capabilities, output = (self.settings.child(name) for name in (CAPABILITIES_NAME, OUTPUT_NAME))
            WaveformOutput.from_settings(capabilities, output).check(samples)
            trigger = None
            if self.settings['trigger'] != NO_TRIGGER:
                trigger = DigitalEdgeTrigger(self.settings['trigger'], EDGES[self.settings['trigger_edge']])
            self.controller.play(samples, output['sample_rate'], OutputMode(output['mode']), output['repetitions'],
                                 self.settings['clock_source'], trigger,
                                 on_done=lambda status: self.emit_status(ThreadCommand('generation_done', status)))
        except Exception as error:  # the move cannot be done: tell it, a move_done would claim a success
            self.emit_status(ThreadCommand('Update_Status', [f'The waveform was not played: {error}', 'log']))
            raise
        self.last_samples = list(samples)
        self.target_value = value
        self.ispolling = False  # the move is done once the generation has started: no polling (set for each move)

    def move_rel(self, value: DataActuator):
        raise ValueError('a waveform has no relative move: send the samples with an absolute move')

    def move_home(self):
        self.stop_motion()

    def stop_motion(self):
        """Stop the generation and bring the outputs to 0 V"""
        if self.controller is not None:
            self.controller.park()


if __name__ == '__main__':
    main(__file__)
