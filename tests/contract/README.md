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
| `Dev1` | simulated card without analog output (model not recorded) | differential-only analog inputs; shows that an unsupported property raises `DaqError` -200197 |
| `Dev2` | PCIe-6363 (X Series) | 32 AI (RSE and differential), 4 AO, 4 counters, `freqout`, digital lines, PFI terminals, start/pause/reference triggers |
| `cDAQ1` | cDAQ-9174 chassis | no channel of its own, only timebases and trigger terminals |
| `cDAQ1Mod1` | NI 9203 | current inputs (0 to 20 mA, -20 to 20 mA) |
| `cDAQ1Mod2` | NI 9213 | thermocouple inputs, only a +-78 mV voltage range (the driver rejects other ranges) |
| `cDAQ1Mod3` | NI 9217 | RTD inputs (3-wire, 1 mA internal excitation) |

Not covered by any device above: the output side of a C Series module (NI 9263, 9401...), and any real
hardware timing. The `reports/contract_report_Dev1.json` file was written by the first version of the
script, so its `system_info` is limited to the AI side and shows the error of the unsupported property.
