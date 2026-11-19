"""Immutable descriptions of what starts a task."""
from dataclasses import dataclass

from nidaqmx.constants import Edge


@dataclass(frozen=True)
class DigitalEdgeTrigger:
    """Start on an edge of a digital terminal such as ``/Dev1/PFI0``."""
    source: str
    edge: Edge = Edge.RISING

    def apply(self, task):
        task.triggers.start_trigger.cfg_dig_edge_start_trig(self.source, self.edge)
