0D viewers DAQmxAI and DAQmxDualAI
==================================

These plugins acquire one (``DAQmxAI``) or two (``DAQmxDualAI``) analog inputs of a NI card, as a voltage between -10 V
and 10 V (differential terminals). They have been ported from the ``pydaqmx`` branch with the same names and settings,
and tested against a fake of the ``nidaqmx`` layer only, not yet on hardware.

Configuration
-------------

* **Display type**: ``0D`` gives the mean value of the samples, ``1D`` gives the trace as a function of time.

* **Frequency Acq.**: the sampling frequency, in Hz.

* **Nsamples**: the number of samples of one acquisition.

* **AI** (``DAQmxAI``) or **AI0** and **AI1** (``DAQmxDualAI``): the analog input channels, something like
  ``Dev[X]/ai[Y]``. The two channels of ``DAQmxDualAI`` are acquired together, with the same clock.

Use
---

The hardware averaging of PyMoDAQ is available: the acquisition is repeated and averaged. For other settings of the
inputs (range, termination, current or temperature), use the general ``NIDAQmx`` viewer.
