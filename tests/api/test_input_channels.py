"""Public API: the kinds of analog input channels (no hardware nor NI-DAQmx driver needed)."""
import pytest

pytest.importorskip('nidaqmx')

from nidaqmx.constants import (ExcitationSource, ResistanceConfiguration, RTDType, TemperatureUnits,
                               TerminalConfiguration, ThermocoupleType)

from nidaqmx_double import driver  # noqa: F401  (pytest fixture)

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AICurrent, AIRtd, AIThermocouple, AIVoltage, AnalogInputTask, ClockSettings, TaskConfig)

CLOCK = ClockSettings(rate=10., samples=2)


def configured_channel(driver, channel):
    AnalogInputTask(TaskConfig(channels=[channel], timing=CLOCK))
    (configured,) = driver[-1].channels
    return configured


def test_a_voltage_channel_can_choose_its_terminal_configuration(driver):
    channel = AIVoltage('Dev1/ai0', terminal_config=TerminalConfiguration.DIFF)

    kind, name, settings = configured_channel(driver, channel)

    assert (kind, name) == ('ai_voltage', 'Dev1/ai0')
    assert settings['terminal_config'] == TerminalConfiguration.DIFF


def test_a_current_channel_measures_within_its_range(driver):
    channel = AICurrent('Dev1/ai1', min_val=0., max_val=0.02)

    kind, name, settings = configured_channel(driver, channel)

    assert (kind, name) == ('ai_current', 'Dev1/ai1')
    assert (settings['min_val'], settings['max_val']) == (0., 0.02)


def test_a_thermocouple_channel_knows_its_type_and_unit(driver):
    channel = AIThermocouple('Dev1/ai2', thermocouple_type=ThermocoupleType.J, units=TemperatureUnits.DEG_F)

    kind, name, settings = configured_channel(driver, channel)

    assert (kind, name) == ('ai_thermocouple', 'Dev1/ai2')
    assert settings['thermocouple_type'] == ThermocoupleType.J
    assert settings['units'] == TemperatureUnits.DEG_F


def test_an_rtd_channel_describes_its_sensor_and_excitation(driver):
    channel = AIRtd('Dev1/ai3', rtd_type=RTDType.PT_3851, resistance_config=ResistanceConfiguration.FOUR_WIRE,
                    excitation_current=0.001)

    kind, name, settings = configured_channel(driver, channel)

    assert (kind, name) == ('ai_rtd', 'Dev1/ai3')
    assert settings['rtd_type'] == RTDType.PT_3851
    assert settings['resistance_config'] == ResistanceConfiguration.FOUR_WIRE
    assert settings['current_excit_source'] == ExcitationSource.INTERNAL
    assert settings['current_excit_val'] == 0.001


def test_a_thermocouple_has_no_terminal_configuration():
    with pytest.raises(TypeError):
        AIThermocouple('Dev1/ai2', terminal_config=TerminalConfiguration.DIFF)


def test_an_rtd_needs_a_positive_excitation_current():
    with pytest.raises(ValueError, match='excitation_current'):
        AIRtd('Dev1/ai3', excitation_current=0.)
