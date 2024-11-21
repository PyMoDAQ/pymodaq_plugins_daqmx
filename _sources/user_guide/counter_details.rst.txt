Details about the implementation of the OD viewer PLcounter
===========================================================

As you have seen from the configuration of the plugin, we use two counter channels to perform the measurement: a first one which is counting and a second one to handle the measurement timing. These are 2 separate tasks, although the channels will be connected together. As a result, we cannot use a single ``DAQmx`` object as hardware controller.

The controller here is a dict containing two ``DAQmx``, one of them is the "clock" and the other the "counter". Each of them contains a single task.

* The clock channel is set up as a ``ClockCounter`` object (see the file ``daqmx.py`` for its definition).
* The counter channel is a ``Counter``, and its timing source is the clock channel.

**Continous grab or snap**

By default, the ``grab_data`` function resets both the clock and the counting tasks. For a single snap, this is not an issue, but for continuous acquisition, this does not make sense, so we use the ``"live"`` parameter sent to ``grab_data`` to decide if we update the tasks or not.
