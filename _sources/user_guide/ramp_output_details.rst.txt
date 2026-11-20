Details about the implementation of the NIDAQmx_RampOutput move
===============================================================

Several channels are needed for a movement: an analog output and a counter used as a clock. As in the case of the
counter (see :doc:`counter_details`), they are separate tasks and a single ``NIDAQmx`` object is not enough. In
addition, with several axes, all the outputs must be in the same task, driven by the same clock, and each axis is a
different instrument plugin: they share a controller, ``RampOutputController`` (``ramp_output.py``).

The controller
--------------

It has two ``NIDAQmx`` objects, ``clock`` and ``analog``, and one ``AOChannel`` per axis. For each move:

* the clock task generates ``n + 1`` pulses at the frequency ``1 / step time``;
* the analog task has one output channel per axis, its sample clock is the internal output of the clock channel, and
  the ``n`` voltages of each axis are written to its buffer.

The axes that are not moved get ``n`` times their current voltage. If another axis is asked to move while a ramp is
running (the Scan extension sends the commands to all the actuators at about the same time), the steps of the running
ramp that are still to do are restarted together with the new one: each axis reaches its target.

Reading the position
--------------------

One cannot read the voltage of an analog output, and the list of voltages is written to the buffer at once, so the last
written value is always the target. The controller estimates the voltage from the time elapsed since the start of the
ramp (the index of the step, one every step time), and returns the final voltage when the ramp is over. The position
is thus an estimate, and the output is set to 0 V when the plugin starts since its real value is unknown.
