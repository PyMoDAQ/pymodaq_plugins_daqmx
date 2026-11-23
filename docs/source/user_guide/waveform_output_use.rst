Waveform output NIDAQmx_Waveform
================================

The actuator ``NIDAQmx_Waveform`` (``DAQ_Move_NIDAQmx_Waveform``) plays **waveforms**, arrays of samples, on several
analog outputs of one NI device at once. The outputs are driven by one task, so they share a sample clock and start
together. For one output set a level at a time, see ``NIDAQmx``; for voltage ramps timed by a counter, see
``NIDAQmx_RampOutput``.

The position of the actuator is a ``DataActuator`` holding one array of samples (in volts) for each chosen output, all
of the same length. The arrays are given in the order of the chosen outputs. The plugin follows the contract of
``pymodaq_plugins_utils.hardware.waveform_output``: the applications that design waveforms, such as the extension of
``pymodaq_plugins_waveform``, read what this device can do and check what they send before they send it.

How to use it
-------------

1. Choose the **Outputs** (the analog outputs of one device, ticked in the list) and their range (**Min**, **Max**).
   Outputs of several devices cannot be in one task: the plugin refuses them. Change them while the actuator runs and
   the outputs go to 0 V before the new ones are driven.
2. In **Waveform output** choose the **Sample rate**, the **Mode** and the number of **Repetitions**:

   * ``finite``: the samples are generated once;
   * ``repeat``: the samples are generated *Repetitions* times;
   * ``continuous``: the samples are generated again and again until the actuator is stopped. The driver repeats the
     samples that were written, so the waveform should hold a whole number of periods.

3. Optionally give an external **Sample clock** (a terminal such as ``/Dev1/PFI1``) and a **Start trigger** (a PFI
   terminal and its edge): the generation then waits for the edge. Without trigger it starts at once.
4. Move the actuator to the samples.

The move is done when the generation has started. The end of a finite or repeated generation is announced by the status
command ``generation_done`` (0 if all went well, else the code of the driver error). The outputs are at 0 V when the
actuator starts, after **stop** and when it closes. When a finite waveform ends, the outputs keep its last sample until
the next waveform or the stop.

Limits
------

The settings group **Waveform capabilities** (read only) shows what the plugin tells to the applications: the
number of outputs, the range of sample rates (``ao_min_rate`` and ``ao_max_rate`` of the device), the voltage range
(the intersection of **Min**, **Max** and the ranges of the device), the modes, the PFI terminals if the device accepts a
start trigger, and **Max samples**.

* The device may be slower than its ``ao_max_rate`` when several outputs are used (some modules share their converter
  between outputs): the driver then refuses the rate and its message is shown.
* **Max samples** is a limit of the plugin (samples per output, to protect the memory), not a figure of the device.
  Set it as you need; a longer waveform is refused with a message.
* A new waveform replaces the one being played **with a break**: the outputs go through 0 V in between
  (``live_update`` is False). To change a waveform without a break, a device that can update its buffer on the fly is
  needed.
* The samples are written to the buffer of the driver before the generation starts: there is no streaming of waveforms
  longer than the buffer.
