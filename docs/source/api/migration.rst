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
     - ``ClockSettings(rate, samples, source, edge)``; no continuous mode yet (``repetition`` has no equivalent)
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
     - ``on_done`` and ``on_samples_ready`` hooks, ``start(notify_every=n)``
   * - ``NIDAQmx.get_NIDAQ_devices()``, ``get_NIDAQ_channels(source_type)``
     - ``NIDAQSystem().devices()``, ``.channels(device, kind)``, ``.all_channels(kind)``
   * - ``getAIMaxSingleRate``, ``getAIMaxMultiRate``, ``getAOMaxRate``
     - ``ai_max_rate(device, multi_channel)``, ``ao_max_rate(device)``
   * - ``getAIVoltageRange``, ``getAOVoltageRange``
     - ``ai_voltage_ranges``, ``ao_voltage_ranges`` (lists of ``(min, max)``)
   * - ``isAnalogTriggeringSupported``, ``isDigitalTriggeringSupported``
     - ``supports_start_trigger(device, 'ai')`` or ``'di'``
   * - ``stop()``, ``start()``, ``close()``
     - the same names on every task, which is also a context manager

Without equivalent for now
--------------------------

* ``isTaskDone`` and ``waitTaskDone``: use ``on_done``.
* The ``repetition`` of a clock (continuous acquisition): the API only describes finite acquisitions for now.
* ``configuration_sequence`` and the ``config_daqmx.toml`` file: they belong to the generic plugins, not to the API,
  and are ported with them.

Things that behave differently
------------------------------

* Mistakes in a description are a ``ValueError`` when you create it, not an ``assert`` or an error swallowed later.
* Driver errors are ``nidaqmx.DaqError`` with an ``error_code``; nothing is turned into an ``IOError``.
* Several plugins do not share a controller any more: each one builds its own task. A multi-axes actuator that needs
  to share something (the clock of the ramp output) shares its own object.
