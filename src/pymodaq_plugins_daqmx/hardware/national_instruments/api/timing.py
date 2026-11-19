"""Immutable descriptions of how a task is clocked."""
from dataclasses import dataclass
from typing import Optional, Tuple

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


@dataclass(frozen=True)
class ImplicitTiming:
    """No sample clock: the task runs on its own signal. Continuous unless ``samples`` is given."""
    samples: Optional[int] = None

    def __post_init__(self):
        if self.samples is not None and not self.samples >= 1:
            raise ValueError(f'samples must be at least 1, got {self.samples}')

    def apply(self, task):
        if self.samples is None:
            task.timing.cfg_implicit_timing(sample_mode=AcquisitionType.CONTINUOUS)
        else:
            task.timing.cfg_implicit_timing(sample_mode=AcquisitionType.FINITE, samps_per_chan=self.samples)


@dataclass(frozen=True)
class ChangeDetectionSettings:
    """Sample on transitions of digital lines. Continuous unless ``samples`` is given."""
    rising_lines: Tuple[str, ...] = ()
    falling_lines: Tuple[str, ...] = ()
    samples: Optional[int] = None

    def __post_init__(self):
        object.__setattr__(self, 'rising_lines', tuple(self.rising_lines))
        object.__setattr__(self, 'falling_lines', tuple(self.falling_lines))
        if not (self.rising_lines or self.falling_lines):
            raise ValueError('change detection needs at least one line, rising or falling')
        if self.samples is not None and not self.samples >= 1:
            raise ValueError(f'samples must be at least 1, got {self.samples}')

    def apply(self, task):
        mode = AcquisitionType.CONTINUOUS if self.samples is None else AcquisitionType.FINITE
        task.timing.cfg_change_detection_timing(
            rising_edge_chan=','.join(self.rising_lines), falling_edge_chan=','.join(self.falling_lines),
            sample_mode=mode, samps_per_chan=1000 if self.samples is None else self.samples)
