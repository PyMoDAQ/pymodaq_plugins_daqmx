Concepts
========

Describe, then run
------------------

Everything that describes a task is a **frozen dataclass**: it is checked when you create it (a ``ValueError`` says
what is wrong, before any driver call), it can be compared, stored, shared between threads and written in a
configuration file.

.. list-table::
   :header-rows: 1

   * - What
     - Objects
   * - Channels
     - ``AIVoltage``, ``AICurrent``, ``AIThermocouple``, ``AIRtd``, ``AOVoltage``, ``AOCurrent``, ``CICountEdges``,
       ``COPulseFreq``, ``DigitalIn``, ``DigitalOut``
   * - Timing
     - ``ClockSettings`` (a sample clock), ``ImplicitTiming`` (no sample clock), ``ChangeDetectionSettings``
       (digital change detection)
   * - Start trigger
     - ``DigitalEdgeTrigger``, ``AnalogEdgeTrigger``
   * - Whole task
     - ``TaskConfig(channels, timing=None, trigger=None)``

A **typed task** is built from a ``TaskConfig``. One class per kind of task: ``AnalogInputTask``,
``AnalogOutputTask``, ``CounterInputTask``, ``CounterOutputTask``, ``DigitalTask``. Each has the verbs that make
sense for it (``read_analog``, ``write_analog``, ``write_levels``, ``read_counter``, ``read_digital``,
``write_digital``) and all share ``start``, ``stop`` and ``close``. A task is also a context manager that closes
itself. To change a setting, close the task and build another one: a configuration never changes.

What comes back
---------------

``read_analog`` returns a ``float64`` array shaped ``(channels, samples)``, always 2D, whatever the number of
channels and samples (the driver itself returns a float, a list or a list of lists depending on the case).
``read_counter`` does the same for counters and ``read_digital`` returns booleans.

Errors
------

* Wrong values in a description are a ``ValueError`` raised when you create it, or when you pass the wrong data to a
  task (for instance data for two channels on a one-channel task).
* Anything the driver refuses is a ``nidaqmx.DaqError``, with its ``error_code``. A read that waits too long is a
  ``nidaqmx.DaqReadError`` (code -200284). There is no ``IOError``.
* Without the NI-DAQmx driver, ``NIDAQSystem`` lists no device, and creating a task raises
  ``nidaqmx.errors.DaqNotFoundError``.

Hardware discovery
------------------

``NIDAQSystem`` tells what the computer's NI hardware offers: devices, channels by kind, terminals, voltage ranges,
maximum rates, whether a start trigger is available. It asks the driver once and remembers the answer until you call
``refresh()``. It returns plain strings, numbers and tuples, so nothing of the driver leaks out.

Clocks and triggers
-------------------

A task with a sample clock takes the clock in ``ClockSettings``. ``source`` is a terminal: empty means the onboard
clock, ``/Dev2/PFI0`` an external signal, and ``counter_output_terminal('Dev2/ctr1')`` the pulses of a counter output
(see the ``counter_rate`` example). A digital line such as ``Dev2/port0/line0`` cannot be used as a trigger source
(the driver refuses it): use a PFI terminal.

Callbacks and threads
---------------------

``start(notify_every=n)`` on an analog input task calls ``on_samples_ready(data)`` for each block of ``n`` samples per
channel, and ``on_done(status)`` is called when the task ends (``status`` is 0 on success). **The driver calls these
from threads of its own**, one per call, and does not guarantee any order between the two. Keep them short and hand
the data over (a queue, a Qt signal); never touch a widget from them. The task keeps the callbacks alive for you: the
driver only holds them weakly.

Other kinds of task do not notify about samples for now.

Good to know
------------

* The driver does not always check ranges (a simulated PCIe-6363 accepts a ±1000 V range). The description objects
  only check that ``min_val < max_val``: use ``NIDAQSystem.ai_voltage_ranges`` if you need more.
* A finite task can be started again after ``stop()``.
* ``read_analog`` waits for the whole acquisition by default (duration plus 5 s); pass ``timeout`` to change it.
