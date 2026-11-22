"""The extensible group of the channels of a settings tree."""
import pytest
from pymodaq_gui.parameter import Parameter

from pymodaq_plugins_daqmx.hardware.national_instruments.api import AIVoltage, AIThermocouple, ChannelKind
from pymodaq_plugins_daqmx.hardware.national_instruments.channel_group import channels_of
from pymodaq_plugins_daqmx.hardware.national_instruments.channel_tree import set_type


def new_group(*names):
    return Parameter.create(name='channels', type='ni_channels', kind='ai', limits=list(names))


def test_the_add_menu_offers_the_channels_that_are_not_in_the_group_yet(qtbot):
    group = new_group('Dev1/ai0', 'Dev1/ai1', 'Dev1/ai2')

    group.addNew('Dev1/ai1')

    assert group.opts['addList'] == ['Dev1/ai0', 'Dev1/ai2']
    assert [child.opts['title'] for child in group.children()] == ['Dev1/ai1']


def test_a_removed_channel_can_be_added_again(qtbot):
    group = new_group('Dev1/ai0', 'Dev1/ai1')
    group.addNew('Dev1/ai0')
    group.addNew('Dev1/ai1')

    group.removeChild(group.children()[0])

    assert group.opts['addList'] == ['Dev1/ai0']


def test_a_channel_cannot_be_added_twice(qtbot):
    group = new_group('Dev1/ai0')
    group.addNew('Dev1/ai0')

    group.addNew('Dev1/ai0')

    assert len(group.children()) == 1


def test_the_channels_of_the_group_are_channels_of_the_api_in_the_order_of_the_group(qtbot):
    group = new_group('Dev1/ai0', 'Dev1/ai1')
    group.addNew('Dev1/ai1')
    group.addNew('Dev1/ai0')
    set_type(ChannelKind.AI, group.children()[1], 'thermocouple')  # what the plugin does when the type changes

    # the range of the voltage channel, which the two types share, is kept
    assert channels_of(group) == [AIVoltage('Dev1/ai1'), AIThermocouple('Dev1/ai0', min_val=-10., max_val=10.)]


def test_the_group_takes_new_limits(qtbot):
    group = new_group('Dev1/ai0', 'Dev1/ai1')
    group.addNew('Dev1/ai0')

    group.setLimits(['Dev2/ai0', 'Dev2/ai1'])

    assert group.opts['addList'] == ['Dev2/ai0', 'Dev2/ai1']
