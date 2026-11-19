"""The complete, immutable description of a task."""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class TaskConfig:
    channels: Tuple
    timing: object

    def __post_init__(self):
        object.__setattr__(self, 'channels', tuple(self.channels))
