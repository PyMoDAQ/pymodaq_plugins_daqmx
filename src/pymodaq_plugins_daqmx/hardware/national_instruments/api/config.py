"""The complete, immutable description of a task."""
from dataclasses import dataclass
from typing import Optional, Tuple, Union

from .channels import (AICurrent, AIRtd, AIThermocouple, AIVoltage, AOCurrent, AOVoltage, CICountEdges,
                       COPulseFreq, DigitalIn, DigitalOut)
from .timing import ChangeDetectionSettings, ClockSettings, ImplicitTiming
from .triggers import AnalogEdgeTrigger, DigitalEdgeTrigger

Channel = Union[AIVoltage, AICurrent, AIThermocouple, AIRtd, AOVoltage, AOCurrent, CICountEdges, COPulseFreq,
                DigitalIn, DigitalOut]
Timing = Union[ClockSettings, ImplicitTiming, ChangeDetectionSettings]
Trigger = Union[DigitalEdgeTrigger, AnalogEdgeTrigger]


@dataclass(frozen=True)
class TaskConfig:
    channels: Tuple[Channel, ...]
    timing: Optional[Timing] = None
    trigger: Optional[Trigger] = None

    def __post_init__(self):
        # the dataclass is frozen, so plain assignment is refused: this is the way to normalise a field once
        object.__setattr__(self, 'channels', tuple(self.channels))
