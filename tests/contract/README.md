# NI-DAQmx contract check

`contract_check.py` records how the real `nidaqmx` package behaves on a NI MAX simulated device
(shapes and dtypes returned by `task.read()`, errors raised for invalid devices, channels, ranges,
rates or triggers, callbacks on a finite task, start/stop/restart, analog and digital writes, counters,
and which kind of analog input channel a module accepts).
The reports are used to model the fake `nidaqmx` module of the unit tests (`tests/api/nidaqmx_double.py`),
which run without hardware or driver.

It is not a pytest test and is not run in CI. Run it by hand on a Windows computer with the NI-DAQmx driver
and a simulated device created in NI MAX:

    pip install nidaqmx
    python contract_check.py Dev2

The result is written to `contract_report_<device>.json` next to the script.
For a cDAQ chassis, run it on each module (`cDAQ1Mod1`, `cDAQ1Mod2`, ...) and not on the chassis itself,
which has no channels of its own. Re-run it when `nidaqmx` is upgraded.

## Devices used for the reference reports

All reports in `reports/` were recorded on NI MAX **simulated** devices, with `nidaqmx` 1.7.0, Python 3.13
on Windows. Simulated devices follow the driver's rules, but not the real timing of a card.

| Device | Product | What it brings |
| --- | --- | --- |
| `Dev1` | PCI-6133 (S Series) | 8 simultaneous AI (differential only, 1.25 to 10 V ranges, 2.5 MS/s), 2 counters, `freqout`, digital lines, no AO; an unsupported property raises `DaqError` -200197; the simulated card accepts voltage, current and thermocouple channels on `ai0` (not RTD: no internal excitation) |
| `Dev2` | PCIe-6363 (X Series) | 32 AI (RSE and differential), 4 AO, 4 counters, `freqout`, digital lines, PFI terminals, start/pause/reference triggers |
| `cDAQ1` | cDAQ-9174 chassis | no channel of its own, only timebases and trigger terminals |
| `cDAQ1Mod1` | NI 9203 | current inputs (0 to 20 mA, -20 to 20 mA) |
| `cDAQ1Mod2` | NI 9213 | thermocouple inputs, only a +-78 mV voltage range (the driver rejects other ranges) |
| `cDAQ1Mod3` | NI 9217 | RTD inputs (3-wire, 1 mA internal excitation) |

Not covered by any device above: the output side of a C Series module (NI 9263, 9401...), and any real
hardware timing. Caution: a simulated card can be more permissive than the real one (the PCI-6133 accepts a
current or thermocouple channel that the real card could not measure), so use the module reports to know which
kind of channel a device accepts. All reports were recorded with the latest `contract_check.py`.
