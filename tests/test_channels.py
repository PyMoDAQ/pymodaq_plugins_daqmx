"""Tests of the description objects of the nidaqmx based interface (no hardware nor NI-DAQmx driver needed)."""
import pytest

pytest.importorskip('nidaqmx')
pytest.importorskip('pymodaq')

from nidaqmx.constants import ChannelType, Edge, UsageTypeCO

from pymodaq_plugins_daqmx.hardware.national_instruments.daqmxni import ClockCounter


class TestClockCounter:
    def test_can_be_instantiated(self):
        clock = ClockCounter(clock_frequency=250., name='Dev1/ctr0')

        assert clock.name == 'Dev1/ctr0'
        assert clock.clock_frequency == 250.
        assert clock.counter_type == UsageTypeCO.PULSE_FREQUENCY
        assert clock.edge == Edge.RISING

    def test_is_a_counter_output_channel_by_default(self):
        assert ClockCounter(name='Dev1/ctr0').source == ChannelType.COUNTER_OUTPUT

    def test_source_can_be_overridden(self):
        clock = ClockCounter(name='Dev1/ctr0', source=ChannelType.COUNTER_OUTPUT, edge=Edge.FALLING)

        assert clock.edge == Edge.FALLING
