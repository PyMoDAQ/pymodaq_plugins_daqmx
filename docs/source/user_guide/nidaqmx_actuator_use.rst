Generic actuators NIDAQmx and NIDAQmx_DO
========================================

Two actuators drive **one output** of an NI device: ``NIDAQmx`` (``DAQ_Move_NIDAQmx``), an analog output (a level in
volts or amperes), and ``NIDAQmx_DO`` (``DAQ_Move_NIDAQmx_DO``), a digital line (0 or 1). They set the output to a value
on demand, one point at a time: there is no clock and no waveform (for voltage ramps, see ``NIDAQmx_RampOutput``). To
drive several outputs, use one actuator for each. The analog one has the *Simple* user interface (a value and a button);
the digital one has the *Binary* interface (one button for each level).

How to use it
-------------

1. Choose the **Output** in the list: the analog outputs (``Dev1/ao0``) of the computer for ``NIDAQmx``, the digital
   lines (``Dev1/port0/line0``) for ``NIDAQmx_DO``.
2. For an analog output, choose the **Type** (``voltage`` or ``current``) and the range of the output (**Min** and
   **Max**, in V or A). The unit of the actuator follows the type.
3. Move the actuator to the level you need. A level outside the range is cut to it, and the plugin says so.

The level of an output cannot be read back from the device, so the value shown is the last level written. The output is
set to 0 (0 V, 0 A or low) when the actuator starts, when you choose another output or another type (the previous
output goes to 0 before the new one is driven) and when the actuator closes.

Digital lines (``NIDAQmx_DO``)
------------------------------

A line is high for a value of 1 and low for 0. The *Pulse* option is for triggering something: a move to 1 then sets
the line high for the **Pulse width** (in ms) and sets it low again, so the position is 0 again afterwards. Wire the line
to a PFI terminal of the device (or of the chassis) and use that terminal as the *Terminal* of the start trigger of a
module of the generic viewers (:doc:`nidaqmx_viewer_use`) to start an acquisition with it.

Using the same device with other plugins
----------------------------------------

An output is used by one task only: the same channel cannot be driven by two actuators, and the driver tells so (the
resource is reserved). Other channels, and the inputs of the same device, remain free.
