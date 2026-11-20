Migrating from the previous objects
===================================

The ``NIDAQmx`` object of ``hardware/national_instruments/daqmxni.py`` (one object, one task, channels described by
mutable classes with a ``source`` attribute, ``update_task`` with several ``if`` on the type) is replaced by the API of
this section. There is no compatibility layer: the old names disappear with the old module, once the plugins of the
package use the new API.

Two lines of releases exist:

* ``5.3.x`` (this branch): ``nidaqmx`` and the new API.
* ``pydaqmx`` (branch and tag ``pydaqmx-final``, also the 1.1.x releases): the ``PyDAQmx`` objects, frozen. Code that
  uses them (laboratory projects, for instance) keeps working by staying on that line. Moving to this API is a
  rewrite of the few places where the task is configured, as shown below.

Before and after
----------------

.. code-block:: python

   # before
   from pymodaq_plugins_daqmx.hardware.national_instruments.daqmxni import (
       NIDAQmx, AIChannel, ClockSettings, ChannelType, UsageTypeAI, TerminalConfiguration)

   controller = NIDAQmx()
   channel = AIChannel(name='Dev1/ai0', source=ChannelType.ANALOG_INPUT, analog_type=UsageTypeAI.VOLTAGE,
                       value_min=-5., value_max=5., termination=TerminalConfiguration.DIFF)
   controller.update_task([channel], ClockSettings(frequency=1000., Nsamples=100, repetition=False))
   controller.task.start()
   raw = controller.task.read(number_of_samples_per_channel=100)   # list or list of lists
   controller.task.stop()
   controller.close()

.. code-block:: python

   # after
   from nidaqmx.constants import TerminalConfiguration
   from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
       AIVoltage, AnalogInputTask, ClockSettings, TaskConfig)

   config = TaskConfig(
       channels=[AIVoltage('Dev1/ai0', min_val=-5., max_val=5., terminal_config=TerminalConfiguration.DIFF)],
       timing=ClockSettings(rate=1000., samples=100))
   with AnalogInputTask(config) as task:
       task.start()
       data = task.read_analog()      # float64 array shaped (1, 100)
       task.stop()

What replaces what
------------------

.. list-table::
   :header-rows: 1

   * - Before
     - After
   * - ``AIChannel`` (voltage), ``AIChannel`` (current)
     - ``AIVoltage``, ``AICurrent`` (``value_min``/``value_max`` become ``min_val``/``max_val``, ``termination``
       becomes ``terminal_config``)
   * - ``AIThermoChannel``, ``AI_RTD_Channel``
     - ``AIThermocouple``, ``AIRtd``
   * - ``AOChannel``
     - ``AOVoltage``, ``AOCurrent``
   * - ``CIChannel`` (count edges)
     - ``CICountEdges``
   * - ``COChannel``, ``ClockCounter``
     - ``COPulseFreq`` (with ``ImplicitTiming``)
   * - ``DIChannel``, ``DOChannel``
     - ``DigitalIn``, ``DigitalOut`` (one line each: use one channel per line)
   * - ``ClockSettings(frequency, Nsamples, source, edge, repetition)``
     - ``ClockSettings(rate, samples, source, edge)``; ``repetition=True`` becomes ``samples=None`` (continuous)
   * - ``ChangeDetectionSettings(rising_channel, falling_channel, Nsamples)``
     - ``ChangeDetectionSettings(rising_lines, falling_lines, samples)``
   * - ``TriggerSettings(trig_source, enable, edge, level)``
     - ``DigitalEdgeTrigger(source, edge)`` or ``AnalogEdgeTrigger(source, level, slope)``; no trigger is ``None``
       instead of ``enable=False``
   * - ``NIDAQmx().update_task(channels, clock, trigger)``
     - ``TaskConfig(channels, timing, trigger)`` given to a typed task (``AnalogInputTask``, ...)
   * - ``controller.task.read(...)``
     - ``read_analog()``, ``read_counter()``, ``read_digital()``: always 2D arrays
   * - ``controller.task.write(...)``
     - ``write_analog()``, ``write_levels()``, ``write_digital()``
   * - ``register_callback(callback, event, nsamples)``
     - ``TaskListener`` (``on_done``, ``on_samples_ready``) given to ``add_listener``, ``start(notify_every=n)``;
       in a plugin, ``QtTaskBridge`` (see below)
   * - ``NIDAQmx.get_NIDAQ_devices()``, ``get_NIDAQ_channels(source_type)``
     - ``NIDAQSystem().devices()``, ``.channels(device, kind)``, ``.all_channels(kind)``
   * - ``getAIMaxSingleRate``, ``getAIMaxMultiRate``, ``getAOMaxRate``
     - ``ai_max_rate(device, multi_channel)``, ``ao_max_rate(device)``
   * - ``getAIVoltageRange``, ``getAOVoltageRange``
     - ``ai_voltage_ranges``, ``ao_voltage_ranges`` (lists of ``(min, max)``)
   * - ``getTriggeringSources``
     - ``terminals(device)``
   * - ``isAnalogTriggeringSupported``, ``isDigitalTriggeringSupported``
     - ``supports_start_trigger(device, 'ai')`` or ``'di'``
   * - ``stop()``, ``start()``, ``close()``
     - the same names on every task, which is also a context manager

Without equivalent for now
--------------------------

* ``isTaskDone`` and ``waitTaskDone``: use ``on_done``.
* ``getAICurrentRange`` and ``getAOCurrentRange`` (current ranges), ``DAQmxGetErrorString`` (use
  ``nidaqmx.constants`` / ``DAQmxErrors`` with ``DaqError.error_code``) and ``readCounter`` (use ``read_counter``).
* ``configuration_sequence`` and the ``config_daqmx.toml`` file: they belong to the generic plugins, not to the API,
  and are ported with them.

Things that behave differently
------------------------------

* Mistakes in a description are a ``ValueError`` when you create it, not an ``assert`` or an error swallowed later.
* Driver errors are ``nidaqmx.DaqError`` with an ``error_code``; nothing is turned into an ``IOError``.
* Several plugins do not share a controller any more: each one builds its own task. A multi-axes actuator that needs
  to share something (the clock of the ramp output) shares its own object.
* A configuration never changes: to change a channel, a rate or a trigger, close the task and build another one. A
  stopped task keeps its channels reserved (driver error -50103), so a second task on the same channels cannot be
  created before the first is closed.
* One task is one subsystem (analog in, analog out, digital, counters). The old object let you try to mix them and
  failed in the driver; the typed tasks make it impossible. Mixing is done with several tasks synchronised by a shared
  clock or trigger, and ``TaskGroup`` to start and stop them in the right order.
* ``read_analog`` on a continuous task is an error: data comes through the listeners.
* Driver callbacks run on threads of the driver, in no guaranteed order.

Porting your own code, step by step
-----------------------------------

1. **Describe** each channel with the class of its kind (table above). Put the arguments that were set after
   creation (``channel.value_min = ...``) in the constructor.
2. **Describe** the timing (``ClockSettings``, ``ChangeDetectionSettings`` or ``ImplicitTiming``) and the trigger
   (``None`` if there is none), and gather everything in a ``TaskConfig``.
3. **Create** the typed task from the config (``with AnalogInputTask(config) as task:`` closes it for you). Replace
   every ``controller.task.<something>`` by the verb of the task (``read_analog``...). The ``nidaqmx.Task`` is no
   longer part of the interface.
4. **Replace the callbacks** by a ``TaskListener``. Do not touch widgets from it: it is called from a driver thread.
5. **Replace** ``update_task`` on a live object by closing the task and building the new one. Code that changed a
   setting when the user edited it (``commit_settings``) rebuilds the config and the task.
6. **Test** with the ``driver`` fixtures of this repository (``tests/nidaqmx_double.py``) or a simulated device of
   NI MAX, then on hardware.

In a PyMoDAQ plugin
-------------------

* The controller of the plugin is the task (or a ``TaskGroup``, or a small object that holds several tasks), not a
  ``NIDAQmx``.
* Create a ``QtTaskBridge`` in ``ini_detector``, register it with ``add_listener`` and connect its ``samples_ready``
  and ``done`` signals to slots of the plugin. Close it before the task, in ``close``.
* A viewer that streams (``live_mode_available = True``) uses a continuous task (``ClockSettings(rate)`` without
  ``samples``) apart from the task used for single grabs: the AI plugins of this package are an example.
* A plugin used as a slave receives the task from the master (``is_master`` is ``False``): it must not close it.

State of the package
--------------------

The AI, counter and ramp-output plugins already use the new API. The generic plugins (``NIDAQmx`` viewers and
actuator, which read ``config_daqmx.toml``) still use the old module ``daqmxni.py`` and are ported next, together with
the removal of the old module: until then, both may be found in the same checkout, but nothing new should be built on
``daqmxni.py``.
