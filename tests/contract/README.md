# NI-DAQmx contract check

`contract_check.py` records how the real `nidaqmx` package behaves on a NI MAX simulated device
(shapes and dtypes returned by `task.read()`, errors raised for invalid devices, channels, ranges,
rates or triggers, callbacks on a finite task, start/stop/restart, analog and digital writes, counters).
The report is used to model the fake `nidaqmx` module of the unit tests, which run without hardware or driver.

It is not a pytest test and is not run in CI. Run it by hand on a Windows computer with the NI-DAQmx driver
and a simulated device created in NI MAX (for instance a PCIe-6363):

    pip install nidaqmx
    python contract_check.py Dev1

The result is written to `contract_report.json` next to the script. Re-run it when `nidaqmx` is upgraded.
