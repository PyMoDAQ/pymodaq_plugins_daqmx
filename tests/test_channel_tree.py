"""The channels of a settings tree: one group for each channel, with only the parameters of its type."""
import pytest
from nidaqmx.constants import (ResistanceConfiguration, RTDType, TemperatureUnits, TerminalConfiguration,
                               ThermocoupleType)
from pymodaq_gui.parameter import Parameter

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (AICurrent, AIRtd, AIThermocouple, AIVoltage,
                                                                      ChannelKind)
from pymodaq_plugins_daqmx.hardware.national_instruments.channel_tree import (channel_from_params, channel_params,
                                                                              set_type)

CHANNELS = [
    AIVoltage('Dev1/ai0', -5., 5., TerminalConfiguration.DIFF),
    AICurrent('Dev1/ai1', -0.02, 0.02, TerminalConfiguration.RSE),
    AIThermocouple('Dev1/ai2', ThermocoupleType.J, TemperatureUnits.DEG_F, 10., 200.),
    AIRtd('Dev1/ai3', RTDType.PT_3750, ResistanceConfiguration.FOUR_WIRE, 0.001, 50., TemperatureUnits.DEG_C,
          -20., 120.),
]


def group(channel):
    return Parameter.create(**channel_params(ChannelKind.AI, channel))


@pytest.mark.parametrize('channel', CHANNELS, ids=lambda c: type(c).__name__)
def test_a_channel_goes_into_the_tree_and_comes_back(qtbot, channel):
    assert channel_from_params(ChannelKind.AI, group(channel)) == channel


def test_a_channel_group_has_the_parameters_of_its_type_only(qtbot):
    thermocouple = group(CHANNELS[2])

    assert thermocouple.name() == 'Dev1/ai2'
    assert [child.name() for child in thermocouple.children()] == [
        'type', 'thermocouple_type', 'units', 'min_val', 'max_val']
    assert thermocouple.child('type').opts['limits'] == ['voltage', 'current', 'thermocouple', 'rtd']
    assert thermocouple.child('thermocouple_type').opts['limits'][:3] == ['J', 'K', 'N']


def test_changing_the_type_replaces_the_parameters_and_keeps_the_ones_in_common(qtbot):
    channel = group(AIThermocouple('Dev1/ai2', min_val=5., max_val=60.))

    set_type(ChannelKind.AI, channel, 'voltage')

    assert [child.name() for child in channel.children()] == ['type', 'min_val', 'max_val', 'terminal_config']
    assert channel.child('type').value() == 'voltage'
    assert (channel.child('min_val').value(), channel.child('max_val').value()) == (5., 60.)
    assert channel_from_params(ChannelKind.AI, channel) == AIVoltage('Dev1/ai2', 5., 60.)


def test_a_range_that_makes_no_sense_names_the_channel(qtbot):
    channel = group(AIVoltage('Dev1/ai0'))
    channel.child('min_val').setValue(20.)

    with pytest.raises(ValueError, match='Dev1/ai0.*lower than'):
        channel_from_params(ChannelKind.AI, channel)
