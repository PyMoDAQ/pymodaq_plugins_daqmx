The NIDAQmx object
==================

You will find its definition in the file ``hardware/national_instruments/daqmxni.py``. This is building block for this plugin, this is the object that you will use as a controller inside your custom plugin.

The ``NIDAQmx`` object has an attribute ``task``, which corresponds to a Task for the NIDAQmx driver. Each ``NIDAQmx`` can only handle a single task, but a task can be executed on several channels. You will find in the same file the definition of many different Channel classes, which are all the channel types that are available physically on such NI devices.

The list of these channels is:

  - AChannel (Analog Channel)

      - AIChannel: Analog Input
      - AIThermoChannel: Specific analog input for thermocouples
      - AOChannel: Analog Output

  - Counter (Regular edge counter)

      - ClockCounter: a counter that you use as a clock
      - SemiPeriodCounter: another specific type of counter which might be useful to count between state transitions of a signal

  - DigitalChannel

      - DOChannel: Digital Output
      - DIChannel: Digital Input

To use the ``NIDAQmx``, you therefore need to create Channels of the type you need, specifying the appropriate ``ClockSettings`` and ``TriggerSettings`` (these are also defined in the same file). Then, you pass these channels to the ``update_task`` method of the ``NIDAQmx``. The ``update_task`` method sets everything up, but if you are using channels as trigger or clock for other channels, you will need to connects them yourself after calling ``update_task``.

Once the task is properly set up, you can start it with the method ``start()`` of the ``NIDAQmx`` object. Depending on the task you are performing, several convenient methods with self-explaining names are available to read or write data:

  - ``read(number_of_samples_per_channel)``: direct measurement (such as in the 0Dviewer)
  - ``register_callback(callback, event, nsamples)``: Measurement using the NI card's buffer (such as in the 1Dviewer)
  - ``write(data, auto_start)``

You can also stop the task with the ``stop()`` method.
