"""Immutable descriptions of how a task is clocked."""
from dataclasses import dataclass

from nidaqmx.constants import AcquisitionType


@dataclass(frozen=True)
class ClockSettings:
    """Acquire ``samples`` samples per channel at ``rate`` Hz."""
    rate: float
    samples: int

    def apply(self, task):
        task.timing.cfg_samp_clk_timing(self.rate, sample_mode=AcquisitionType.FINITE,
                                        samps_per_chan=self.samples)
