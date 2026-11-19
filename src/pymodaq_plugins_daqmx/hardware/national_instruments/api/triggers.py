"""Immutable descriptions of what starts a task."""
from dataclasses import dataclass

from nidaqmx.constants import Edge, Slope


@dataclass(frozen=True)
class DigitalEdgeTrigger:
    """Start on an edge of a digital terminal such as ``/Dev1/PFI0``."""
    source: str
    edge: Edge = Edge.RISING

    def apply_to(self, task):
        task.triggers.start_trigger.cfg_dig_edge_start_trig(self.source, self.edge)


@dataclass(frozen=True)
class AnalogEdgeTrigger:
    """Start when the analog signal ``source`` (a channel such as ``Dev1/ai0``) crosses ``level``."""
    source: str
    level: float
    slope: Slope = Slope.RISING

    def apply_to(self, task):
        task.triggers.start_trigger.cfg_anlg_edge_start_trig(self.source, self.slope, self.level)
