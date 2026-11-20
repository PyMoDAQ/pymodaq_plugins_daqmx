Details about the implementation of the 0D viewer DAQmx_Counter
===============================================================

Two counters are used for one measurement: a first one counts the edges and a second one gives the counting time.
These are two separate tasks, although the channels are connected together, so a single ``NIDAQmx`` object cannot be
the controller of the plugin.

The controller is a dict containing two ``NIDAQmx`` objects, ``clock`` and ``counter``, each with its own task:

* The clock is a ``ClockCounter`` channel (see ``daqmxni.py``), producing pulses at the clock frequency.
* The counter is a ``CIChannel`` counting edges, whose sample clock is the internal output of the clock channel
  (``/Dev[X]/ctr[Y]InternalOutput``): one sample is taken at the first tick of the clock.

**One grab**

Each grab arms the counting task (it waits for the clock), starts the clock, reads the one sample and stops both
tasks. The count rate is the number of counted edges divided by the counting time, ``1 / clock frequency``. In live
mode, the viewer calls the grab again and again. Changing a setting stops the tasks and creates them again.
