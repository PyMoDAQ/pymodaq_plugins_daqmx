"""Immutable descriptions of the channels of a task."""
from dataclasses import dataclass

from nidaqmx.constants import (CountDirection, CurrentUnits, Edge, ExcitationSource, Level,
                               ResistanceConfiguration, RTDType, TemperatureUnits, TerminalConfiguration,
                               ThermocoupleType, VoltageUnits)


def _check_range(min_val, max_val):
    if not min_val < max_val:
        raise ValueError(f'min_val ({min_val}) must be lower than max_val ({max_val})')


@dataclass(frozen=True)
class AIVoltage:
    """Analog input measuring a voltage on a physical channel such as ``Dev1/ai0``."""
    name: str
    min_val: float = -10.
    max_val: float = 10.
    terminal_config: TerminalConfiguration = TerminalConfiguration.DEFAULT

    def __post_init__(self):
        _check_range(self.min_val, self.max_val)

    def add_to(self, task):
        task.ai_channels.add_ai_voltage_chan(self.name, terminal_config=self.terminal_config,
                                             min_val=self.min_val, max_val=self.max_val,
                                             units=VoltageUnits.VOLTS)


@dataclass(frozen=True)
class AICurrent:
    """Analog input measuring a current, in amperes."""
    name: str
    min_val: float = -0.02
    max_val: float = 0.02
    terminal_config: TerminalConfiguration = TerminalConfiguration.DEFAULT

    def __post_init__(self):
        _check_range(self.min_val, self.max_val)

    def add_to(self, task):
        task.ai_channels.add_ai_current_chan(self.name, terminal_config=self.terminal_config,
                                             min_val=self.min_val, max_val=self.max_val,
                                             units=CurrentUnits.AMPS)


@dataclass(frozen=True)
class AIThermocouple:
    """Analog input measuring a temperature with a thermocouple (no terminal configuration)."""
    name: str
    thermocouple_type: ThermocoupleType = ThermocoupleType.K
    units: TemperatureUnits = TemperatureUnits.DEG_C
    min_val: float = 0.
    max_val: float = 100.

    def __post_init__(self):
        _check_range(self.min_val, self.max_val)

    def add_to(self, task):
        task.ai_channels.add_ai_thrmcpl_chan(self.name, min_val=self.min_val, max_val=self.max_val,
                                             units=self.units, thermocouple_type=self.thermocouple_type)


@dataclass(frozen=True)
class AIRtd:
    """Analog input measuring a temperature with a resistance temperature detector."""
    name: str
    rtd_type: RTDType = RTDType.PT_3851
    resistance_config: ResistanceConfiguration = ResistanceConfiguration.THREE_WIRE
    excitation_current: float = 0.0025
    r_0: float = 100.
    units: TemperatureUnits = TemperatureUnits.DEG_C
    min_val: float = 0.
    max_val: float = 100.

    def __post_init__(self):
        _check_range(self.min_val, self.max_val)
        if not self.excitation_current > 0:
            raise ValueError(f'excitation_current must be positive, got {self.excitation_current}')

    def add_to(self, task):
        task.ai_channels.add_ai_rtd_chan(
            self.name, min_val=self.min_val, max_val=self.max_val, units=self.units,
            rtd_type=self.rtd_type, resistance_config=self.resistance_config,
            current_excit_source=ExcitationSource.INTERNAL, current_excit_val=self.excitation_current,
            r_0=self.r_0)


@dataclass(frozen=True)
class AOVoltage:
    """Analog output generating a voltage on a physical channel such as ``Dev2/ao0``."""
    name: str
    min_val: float = -10.
    max_val: float = 10.

    def __post_init__(self):
        _check_range(self.min_val, self.max_val)

    def add_to(self, task):
        task.ao_channels.add_ao_voltage_chan(self.name, min_val=self.min_val, max_val=self.max_val,
                                             units=VoltageUnits.VOLTS)


@dataclass(frozen=True)
class AOCurrent:
    """Analog output generating a current, in amperes."""
    name: str
    min_val: float = 0.
    max_val: float = 0.02

    def __post_init__(self):
        _check_range(self.min_val, self.max_val)

    def add_to(self, task):
        task.ao_channels.add_ao_current_chan(self.name, min_val=self.min_val, max_val=self.max_val,
                                             units=CurrentUnits.AMPS)


@dataclass(frozen=True)
class CICountEdges:
    """Counter input counting the edges of a signal, starting from ``initial_count``."""
    name: str
    edge: Edge = Edge.RISING
    initial_count: int = 0
    direction: CountDirection = CountDirection.COUNT_UP

    def add_to(self, task):
        task.ci_channels.add_ci_count_edges_chan(self.name, edge=self.edge, initial_count=self.initial_count,
                                                 count_direction=self.direction)


@dataclass(frozen=True)
class COPulseFreq:
    """Counter output generating a pulse train of the given frequency (Hz) and duty cycle (0 to 1, excluded)."""
    name: str
    frequency: float
    duty_cycle: float = 0.5
    idle_state: Level = Level.LOW
    initial_delay: float = 0.

    def __post_init__(self):
        if not self.frequency > 0:
            raise ValueError(f'frequency must be positive, got {self.frequency}')
        if not 0 < self.duty_cycle < 1:
            raise ValueError(f'duty_cycle must be between 0 and 1 (excluded), got {self.duty_cycle}')

    def add_to(self, task):
        task.co_channels.add_co_pulse_chan_freq(self.name, freq=self.frequency, duty_cycle=self.duty_cycle,
                                                idle_state=self.idle_state, initial_delay=self.initial_delay)
