0D viewer DAQmx_Counter
=======================

This plugin counts the edges (rising by default) of a signal sent to a counter input of a NI card, for instance the TTL
pulses of a single photon detector such as an avalanche photodiode (APD). It gives the count rate in counts/s (the
unit of the data is ``counts/s``).

It replaces ``DAQmx_PLcounter`` of the ``pydaqmx`` branch, which was tested only with NI PCIe 63XX devices. The present
version has been tested against a fake of the ``nidaqmx`` layer only, not yet on hardware.

Configuration
-------------

* **Counting channel**: the counter that counts the edges of the signal, something like ``Dev[X]/ctr[Y]``. The signal
  must be wired to the default input terminal of this counter, check the documentation of your NI device about it.

* **Clock channel**: the counter used to time the measurement, something like ``Dev[X]/ctr[Y]``. It cannot be the same
  as the counting channel.

* **Clock frequency**: the acquisition rate in Hz. Each point is the number of edges counted during one period of the
  clock (the counting time), divided by this time.

Use
---

It works as a usual 0D viewer plugin. If you need to use one of the counter channels with another plugin, stop the
measurement first, otherwise you will get an error about the resource being busy.
