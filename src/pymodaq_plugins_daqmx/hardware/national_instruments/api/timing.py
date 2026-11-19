"""Immutable descriptions of how a task is clocked."""
from dataclasses import dataclass

from nidaqmx.constants import AcquisitionType, Edge


@dataclass(frozen=True)
class ClockSettings:
    """Acquire ``samples`` samples per channel at ``rate`` Hz.

    ``source`` is a terminal such as ``/Dev1/PFI1`` to use an external clock; empty means the onboard clock.
    """
    rate: float
    samples: int
    source: str = ''
    edge: Edge = Edge.RISING

    def __post_init__(self):
        if not self.rate > 0:
            raise ValueError(f'rate must be positive, got {self.rate}')
        if not self.samples >= 1:
            raise ValueError(f'samples must be at least 1, got {self.samples}')

    def apply(self, task):
        task.timing.cfg_samp_clk_timing(self.rate, source=self.source, active_edge=self.edge,
                                        sample_mode=AcquisitionType.FINITE, samps_per_chan=self.samples)
