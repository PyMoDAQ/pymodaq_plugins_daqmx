The DAQmx object
================

You will find its definition in the file ``hardware/national_instruments/daqmx.py``. This is building block for this plugin, this is the object that you will use as a controller inside your custom plugin.

The ``DAQmx`` object has an attribute ``task``, which corresponds to a Task for the NIDAQmx driver. Each ``DAQmx`` can only handle a single task, but a task can be executed on several channels. You will find in the same file the definition of many different Channel classes, which are all the channel types that are available physically on such NI devices.

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

To use the ``DAQmx``, you therefore need to create Channels of the type you need, specifying the appropriate ``ClockSettings`` and ``TriggerSettings`` (these are also defined in the same file). Then, you pass these channels to the ``update_task`` method of the ``DAQmx``. Be careful that a task can only handle one channel type, if you need several, you need several ``DAQmx``. The ``update_task`` method sets everything up, but if you are using channels as trigger or clock for other channels, you will need to connects them yourself after calling ``update_task``.

Once the task is properly set up, you can start it with the method ``start()`` of the ``DAQmx`` object. Several convenient methods of the ``DAQmx`` object are available to read or write data, depending on the task you are performing. They have self-explaining names:

   - ``writeAnalog(Nsamples, Nchannels, values, autostart=False)``
   - ``readAnalog(Nchannels)``
   - ``readCounter(Nchannels, counting_time=10., read_function='Ex')``
   - ``readDigital(Nchannels)``
   - ``writeDigital(Nchannes, values, autostart=False)``

You can also stop the task with the ``stop()`` method.
