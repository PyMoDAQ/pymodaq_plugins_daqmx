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

    def apply_to(self, task):
        task.timing.cfg_samp_clk_timing(self.rate, source=self.source, active_edge=self.edge,
                                        sample_mode=AcquisitionType.FINITE, samps_per_chan=self.samples)


@dataclass(frozen=True)
class ImplicitTiming:
    """No sample clock: the pace is given by the task itself, not by the onboard clock.

    Use it for counter output: the counter itself generates the pulse train (continuous, or ``samples`` pulses).
    For a counter input that is read on demand, give no timing at all (``timing=None``): each read returns the
    count at the moment of the call. To count at a regular pace, use ``ClockSettings`` with a ``source``.
    """
    samples: Optional[int] = None

    def __post_init__(self):
        if self.samples is not None and not self.samples >= 1:
            raise ValueError(f'samples must be at least 1, got {self.samples}')

    def apply_to(self, task):
        if self.samples is None:
            task.timing.cfg_implicit_timing(sample_mode=AcquisitionType.CONTINUOUS)
        else:
            task.timing.cfg_implicit_timing(sample_mode=AcquisitionType.FINITE, samps_per_chan=self.samples)


@dataclass(frozen=True)
class ChangeDetectionSettings:
    """Sample a digital input task on transitions of the chosen lines, instead of on a clock.

    Example: ``TaskConfig((DigitalIn('Dev1/port0/line0'),),
    timing=ChangeDetectionSettings(rising_lines=('Dev1/port0/line0',)))``, run with a ``DigitalTask``.
    Continuous unless ``samples`` is given.
    """
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

    def apply_to(self, task):
        mode = AcquisitionType.CONTINUOUS if self.samples is None else AcquisitionType.FINITE
        task.timing.cfg_change_detection_timing(
            rising_edge_chan=','.join(self.rising_lines), falling_edge_chan=','.join(self.falling_lines),
            sample_mode=mode, samps_per_chan=1000 if self.samples is None else self.samples)


def counter_output_terminal(counter: str) -> str:
    """The terminal where a counter output sends its pulses, such as ``/Dev1/Ctr1InternalOutput`` for
    ``Dev1/ctr1``: give it as ``source`` of a ``ClockSettings`` to clock another task with these pulses."""
    device, _, channel = counter.partition('/')
    if not (device and channel.startswith('ctr') and channel[3:].isdigit()):
        raise ValueError(f'{counter!r} is not a counter such as Dev1/ctr0')
    return f'/{device}/Ctr{channel[3:]}InternalOutput'
