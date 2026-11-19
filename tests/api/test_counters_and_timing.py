"""Public API: counters, implicit timing, change detection and analog triggers (no hardware nor driver)."""
import numpy as np
import pytest

pytest.importorskip('nidaqmx')

from nidaqmx.constants import AcquisitionType, CountDirection, Edge, Level, Slope

from nidaqmx_double import driver  # noqa: F401  (pytest fixture)

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AIVoltage, AnalogEdgeTrigger, AnalogInputTask, ChangeDetectionSettings, CICountEdges, ClockSettings,
    COPulseFreq, CounterInputTask, CounterOutputTask, ImplicitTiming, TaskConfig)


def configured_channel(driver):
    (configured,) = driver[-1].channels
    return configured


def test_a_counter_input_counts_edges_from_a_starting_value(driver):
    channel = CICountEdges('Dev2/ctr0', edge=Edge.FALLING, initial_count=5, direction=CountDirection.COUNT_DOWN)

    CounterInputTask(TaskConfig(channels=[channel]))

    kind, name, settings = configured_channel(driver)
    assert (kind, name) == ('ci_count_edges', 'Dev2/ctr0')
    assert settings['edge'] == Edge.FALLING
    assert settings['initial_count'] == 5
    assert settings['count_direction'] == CountDirection.COUNT_DOWN


def test_counts_are_read_as_a_2d_float_array_clocked_by_another_signal(driver):
    config = TaskConfig(channels=[CICountEdges('Dev2/ctr0')],
                        timing=ClockSettings(rate=1000., samples=3, source='/Dev2/PFI0'))

    with CounterInputTask(config) as task:
        counts = task.read_counter()

    assert counts.dtype == np.float64
    assert counts.shape == (1, 3)


def test_a_counter_output_generates_a_pulse_train_until_stopped(driver):
    channel = COPulseFreq('Dev2/ctr1', frequency=2000., duty_cycle=0.25)
    config = TaskConfig(channels=[channel], timing=ImplicitTiming())

    with CounterOutputTask(config) as task:
        task.start()

    nidaqmx_task = driver[-1]
    kind, name, settings = nidaqmx_task.channels[0]
    assert (kind, name) == ('co_pulse_freq', 'Dev2/ctr1')
    assert (settings['freq'], settings['duty_cycle'], settings['idle_state']) == (2000., 0.25, Level.LOW)
    assert nidaqmx_task.timing_calls == [('implicit', AcquisitionType.CONTINUOUS, 1000)]
    assert nidaqmx_task.started


@pytest.mark.parametrize('kwargs', [dict(frequency=0.), dict(frequency=10., duty_cycle=0.),
                                    dict(frequency=10., duty_cycle=1.)])
def test_a_pulse_train_that_cannot_exist_is_refused(kwargs):
    with pytest.raises(ValueError):
        COPulseFreq('Dev2/ctr1', **kwargs)


def test_a_finite_implicit_timing_stops_after_its_samples(driver):
    config = TaskConfig(channels=[COPulseFreq('Dev2/ctr1', frequency=10.)], timing=ImplicitTiming(samples=50))

    CounterOutputTask(config)

    assert driver[-1].timing_calls == [('implicit', AcquisitionType.FINITE, 50)]


def test_change_detection_samples_on_transitions_of_the_chosen_lines(driver):
    timing = ChangeDetectionSettings(rising_lines=['Dev2/port0/line0', 'Dev2/port0/line1'],
                                     falling_lines=['Dev2/port0/line0'])
    config = TaskConfig(channels=[AIVoltage('Dev2/ai0')], timing=timing)

    AnalogInputTask(config)

    assert driver[-1].timing_calls == [('change_detection', 'Dev2/port0/line0,Dev2/port0/line1',
                                        'Dev2/port0/line0', AcquisitionType.CONTINUOUS, 1000)]


def test_change_detection_needs_at_least_one_line():
    with pytest.raises(ValueError, match='line'):
        ChangeDetectionSettings()


def test_an_analog_edge_trigger_waits_for_a_level(driver):
    trigger = AnalogEdgeTrigger(source='Dev2/ai0', level=1.5, slope=Slope.FALLING)
    config = TaskConfig(channels=[AIVoltage('Dev2/ai0')], timing=ClockSettings(rate=100., samples=2),
                        trigger=trigger)

    AnalogInputTask(config)

    assert driver[-1].trigger_calls == [('anlg_edge', 'Dev2/ai0', Slope.FALLING, 1.5)]
