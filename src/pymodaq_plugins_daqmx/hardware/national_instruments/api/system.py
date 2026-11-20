"""What the NI hardware of the computer offers: devices, channels, terminals, ranges, rates, triggers."""
from typing import List

import nidaqmx.errors
import nidaqmx.system
from nidaqmx.constants import TriggerUsage
from pymodaq_utils.enums import StrEnum


class ChannelKind(StrEnum):
    """Kinds of channels of a device. Members compare equal to their value: ``'ai'``, ``'ci'``..."""
    AI = 'ai'
    AO = 'ao'
    CI = 'ci'
    CO = 'co'
    DI = 'di'  # lines
    DO = 'do'  # lines


_CHANNEL_ATTRIBUTES = {
    ChannelKind.AI: 'ai_physical_chans', ChannelKind.AO: 'ao_physical_chans', ChannelKind.CI: 'ci_physical_chans',
    ChannelKind.CO: 'co_physical_chans', ChannelKind.DI: 'di_lines', ChannelKind.DO: 'do_lines',
}
_UNSUPPORTED_PROPERTY = -200197


class NIDAQSystem:
    """A view of the NI hardware, read from the driver once and kept until ``refresh()``.

    Without the NI-DAQmx driver there is simply no device. Everything returned is made of plain strings,
    numbers and tuples. A device or a kind of channel that does not exist is a ``ValueError``; a property the
    device does not have (for instance the maximum rate of the analog outputs of a card without any) is
    ``None`` or an empty list.
    """

    def __init__(self):
        self._cache = {}

    def refresh(self):
        """Forget what was read: the next call asks the driver again (a card may have been plugged in)."""
        self._cache = {}

    def devices(self):
        """Names of the devices, such as ``['Dev1', 'Dev2']``; empty without driver."""
        return list(self._remember('devices', self._read_devices))

    def channels(self, device: str, kind: ChannelKind) -> List[str]:
        """Names of the channels of ``device`` (such as ``'Dev1'``) of the given ``kind`` (a `ChannelKind` or its
        value: ai, ao, ci, co, di (lines) or do (lines))."""
        try:
            kind = ChannelKind(kind)
        except ValueError:
            raise ValueError(f'unknown kind {kind!r} of channel: use one of {ChannelKind.values()}') from None
        return list(self._device_property(device, _CHANNEL_ATTRIBUTES[kind], lambda value: value.channel_names, []))

    def all_channels(self, kind: ChannelKind) -> List[str]:
        """Names of the channels of the given ``kind`` on all the devices, device after device."""
        return [channel for device in self.devices() for channel in self.channels(device, kind)]

    def terminals(self, device):
        """Terminals of ``device`` (``/Dev1/PFI0``...), usable as clock or trigger sources."""
        return list(self._device_property(device, 'terminals', list, []))

    def ai_voltage_ranges(self, device):
        """Voltage ranges of the analog inputs as ``(min, max)`` pairs."""
        return self._device_property(device, 'ai_voltage_rngs', _pairs, [])

    def ao_voltage_ranges(self, device):
        """Voltage ranges of the analog outputs as ``(min, max)`` pairs."""
        return self._device_property(device, 'ao_voltage_rngs', _pairs, [])

    def ai_max_rate(self, device, multi_channel=True):
        """Maximum sampling rate (Hz) of the analog inputs, for several channels or for a single one."""
        name = 'ai_max_multi_chan_rate' if multi_channel else 'ai_max_single_chan_rate'
        return self._device_property(device, name, float, None)

    def ao_max_rate(self, device):
        """Maximum update rate (Hz) of the analog outputs; ``None`` if the device has none."""
        return self._device_property(device, 'ao_max_rate', float, None)

    def supports_start_trigger(self, device, kind):
        """Whether a ``kind`` (``ChannelKind.AI`` or ``ChannelKind.DI``) task on ``device`` can wait for a start trigger."""
        if kind not in (ChannelKind.AI, ChannelKind.DI):
            raise ValueError(f"unknown kind {kind!r}: triggers are supported by AI and DI tasks")
        usage = self._device_property(device, f'{kind}_trig_usage', list, [])
        return TriggerUsage.START in usage

    def _read_devices(self):
        try:
            return list(nidaqmx.system.System.local().devices.device_names)
        except nidaqmx.errors.DaqNotFoundError:  # the NI-DAQmx driver is not installed
            return []

    def _remember(self, key, read):
        if key not in self._cache:
            self._cache[key] = read()
        return self._cache[key]

    def _device_property(self, device, name, convert, when_unsupported):
        known = self.devices()
        if device not in known:
            raise ValueError(f'unknown device {device!r}: known devices are {", ".join(known) or "none"}')

        def read():
            try:
                return convert(getattr(nidaqmx.system.System.local().devices[device], name))
            except nidaqmx.errors.DaqError as error:
                if error.error_code == _UNSUPPORTED_PROPERTY:
                    return when_unsupported
                raise

        return self._remember((device, name), read)


def _pairs(flat):
    flat = list(flat)
    return [(float(flat[i]), float(flat[i + 1])) for i in range(0, len(flat), 2)]
