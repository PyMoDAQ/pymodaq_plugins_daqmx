NIDAQmx_RampOutput move
=======================

This plugin uses an analog output of a NI device to drive a quantity (a position, for instance) by changing the output
voltage in a succession of steps, at a chosen speed. The value is the voltage times a conversion factor, in nm/V. It
was written for the XY scanning of a scanning probe microscope with a voltage amplifier between the NI card and the
scanner, where slow movements are wanted on purpose, but it works with anything that takes a voltage as input.

It replaces ``DAQmx_ScannerControl`` and ``DAQmx_MultipleScannerControl`` of the ``pydaqmx`` branch: a single
multi-axes plugin (axes x, y, z) which also drives a single output. It has been tested against a fake of the
``nidaqmx`` layer only, not yet on hardware.

Configuration
-------------

* **Output channel**: the output of the NI card connected to the load, something like ``Dev[X]/ao[Y]``.

* **Clock channel**: the counter timing the steps (and so the speed), something like ``Dev[X]/ctr[Y]``. Only the
  settings of the master are used.

* **Step size**: in nm.

* **Step time**: in ms. The step size and the step time set the speed.

* **Conversion factor**: in nm/V, the coefficient between the output voltage and the value.

* **Bounds**: set them to the range reachable by your device. The output of the card can go from -10 V to 10 V.

Several axes
++++++++++++

The number of counters of a NI card is small, so the axes share the same clock. Create the first axis (it is the
master, it creates the controller and owns the clock) and give to the other ones the same controller ID, with a
different axis. Each axis has its own output channel, step size and conversion factor. The step time and the clock are
those of the master.

Use
---

This plugin works as a regular daq move plugin.

**One cannot read the voltage of an analog output**, so the plugin cannot know the position when it starts: the output
is set to 0 V at the initialization, in a single step. Be careful to go back to the rest position before closing.

If you ask for a change larger than the step size, the voltages are sent to the card as a list (a ramp), one value
every step time. The position displayed is the one expected from the time elapsed since the start of the ramp. The stop
button stops the ramp where it is. During a scan, avoid several steps between two pixels: set the step size of the
plugin larger than the step of the Scan extension.

If you need to use the clock channel with another plugin, stop the movement first, otherwise you will get an error
about the resource being busy.
