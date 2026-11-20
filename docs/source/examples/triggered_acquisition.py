"""Wait for an edge on a PFI terminal before acquiring."""
from nidaqmx.constants import Edge

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AIVoltage, AnalogInputTask, ChannelKind, ClockSettings, DigitalEdgeTrigger, NIDAQSystem, TaskConfig)


def main(device='Dev2'):
    system = NIDAQSystem()
    if not system.supports_start_trigger(device, ChannelKind.AI):
        raise RuntimeError(f'{device} cannot wait for a start trigger')
    pfi = next(terminal for terminal in system.terminals(device) if 'PFI' in terminal)  # e.g. /Dev2/PFI0
    config = TaskConfig(channels=[AIVoltage(f'{device}/ai0')],
                        timing=ClockSettings(rate=1000., samples=100),
                        trigger=DigitalEdgeTrigger(pfi, edge=Edge.RISING))
    with AnalogInputTask(config) as task:
        task.start()  # armed, nothing is acquired until the edge arrives
        return task.read_analog(timeout=10.)  # give the experiment time to send its edge


if __name__ == '__main__':
    print(main().shape)
