"""Public API: what the computer's NI hardware offers (no hardware nor NI-DAQmx driver needed)."""
import pytest

pytest.importorskip('nidaqmx')

from nidaqmx_double import system_driver, _pcie_6363  # noqa: F401  (pytest fixture)

from pymodaq_plugins_daqmx.hardware.national_instruments.api import ChannelKind, NIDAQSystem


def test_lists_the_devices_as_plain_strings(system_driver):
    assert NIDAQSystem().devices() == ['Dev1', 'Dev2']


def test_without_the_driver_there_is_simply_no_device(system_driver):
    system_driver.driver_present = False

    system = NIDAQSystem()

    assert system.devices() == []


def test_lists_the_channels_of_a_device_by_kind(system_driver):
    system = NIDAQSystem()

    assert system.channels('Dev2', 'ai')[:2] == ['Dev2/ai0', 'Dev2/ai1']
    assert len(system.channels('Dev2', 'ai')) == 32
    assert system.channels('Dev2', 'co')[-1] == 'Dev2/freqout'
    assert system.channels('Dev2', 'do')[0] == 'Dev2/port0/line0'
    assert system.channels('Dev1', 'ao') == []


def test_asking_for_an_unknown_kind_of_channel_is_an_error(system_driver):
    with pytest.raises(ValueError, match='kind'):
        NIDAQSystem().channels('Dev2', 'xx')


def test_lists_the_terminals_usable_as_clock_or_trigger_sources(system_driver):
    assert NIDAQSystem().terminals('Dev2')[:2] == ['/Dev2/PFI0', '/Dev2/PFI1']


def test_voltage_ranges_are_min_max_pairs(system_driver):
    system = NIDAQSystem()

    assert system.ai_voltage_ranges('Dev2') == [(-0.1, 0.1), (-0.2, 0.2), (-0.5, 0.5), (-1.0, 1.0),
                                                (-2.0, 2.0), (-5.0, 5.0), (-10.0, 10.0)]
    assert system.ao_voltage_ranges('Dev2') == [(-5.0, 5.0), (-10.0, 10.0)]
    assert system.ao_voltage_ranges('Dev1') == []


def test_maximum_rates_and_the_lack_of_one(system_driver):
    system = NIDAQSystem()

    assert system.ai_max_rate('Dev2') == 1000000.0
    assert system.ai_max_rate('Dev2', multi_channel=False) == 2000000.0
    assert system.ao_max_rate('Dev2') == pytest.approx(2857142.857)
    assert system.ao_max_rate('Dev1') is None  # the PCI-6133 has no analog output


def test_tells_whether_a_device_can_be_started_by_a_trigger(system_driver):
    system = NIDAQSystem()

    assert system.supports_start_trigger('Dev2', 'ai') is True
    assert system.supports_start_trigger('Dev2', 'di') is True
    assert system.supports_start_trigger('Dev1', 'di') is False


def test_an_unknown_device_is_an_error_naming_the_known_ones(system_driver):
    with pytest.raises(ValueError, match='Dev1, Dev2'):
        NIDAQSystem().terminals('Dev9')


def test_the_view_of_the_hardware_is_kept_until_refreshed(system_driver):
    system = NIDAQSystem()
    assert system.devices() == ['Dev1', 'Dev2']

    new = _pcie_6363()
    new.name = 'Dev3'
    system_driver.installed_devices.append(new)

    assert system.devices() == ['Dev1', 'Dev2']
    system.refresh()
    assert system.devices() == ['Dev1', 'Dev2', 'Dev3']


def test_lists_the_channels_of_all_the_devices_by_kind(system_driver):
    system = NIDAQSystem()

    channels = system.all_channels('ai')

    assert channels[0] == 'Dev1/ai0' and channels[7] == 'Dev1/ai7'
    assert channels[8] == 'Dev2/ai0' and len(channels) == 8 + 32
    assert system.all_channels('ao') == [f'Dev2/ao{c}' for c in range(4)]
    assert system.all_channels(ChannelKind.AO) == system.all_channels('ao')


def test_all_channels_is_empty_without_the_driver(system_driver):
    system_driver.driver_present = False

    assert NIDAQSystem().all_channels('ai') == []
