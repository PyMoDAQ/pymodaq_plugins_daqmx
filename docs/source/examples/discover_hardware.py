"""List what the computer's NI hardware offers, without creating any task."""
from pymodaq_plugins_daqmx.hardware.national_instruments.api import NIDAQSystem


def main():
    system = NIDAQSystem()
    report = {}
    for device in system.devices():
        report[device] = {
            'analog inputs': system.channels(device, 'ai'),
            'analog outputs': system.channels(device, 'ao'),
            'voltage ranges (V)': system.ai_voltage_ranges(device),
            'terminals': system.terminals(device),
            'max analog input rate (Hz)': system.ai_max_rate(device, multi_channel=False),
        }
    return report


if __name__ == '__main__':
    for device, properties in main().items():
        print(device, properties)
