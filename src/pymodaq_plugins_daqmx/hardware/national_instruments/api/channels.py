"""Immutable descriptions of the channels of a task."""
from dataclasses import dataclass


@dataclass(frozen=True)
class AIVoltage:
    """Analog input measuring a voltage on a physical channel such as ``Dev1/ai0``."""
    name: str
    min_val: float = -10.
    max_val: float = 10.

    def __post_init__(self):
        if not self.min_val < self.max_val:
            raise ValueError(f'min_val ({self.min_val}) must be lower than max_val ({self.max_val})')

    def add_to(self, task):
        task.ai_channels.add_ai_voltage_chan(self.name, min_val=self.min_val, max_val=self.max_val)
