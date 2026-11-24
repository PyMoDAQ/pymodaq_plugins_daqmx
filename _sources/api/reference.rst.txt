Reference
=========

.. automodule:: pymodaq_plugins_daqmx.hardware.national_instruments.api
   :no-members:

System
------

.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.NIDAQSystem
   :members:

Tasks
-----

.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.TaskConfig

.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.AnalogInputTask
   :members: read_analog, start, stop, close, add_listener, remove_listener

.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.TaskListener
   :members:

.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.AnalogOutputTask
   :members: write_analog, write_levels, start, stop, close

.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.CounterInputTask
   :members: read_counter, start, stop, close

.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.CounterOutputTask
   :members: start, stop, close

.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.DigitalTask
   :members: read_digital, write_digital, start, stop, close

.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.TaskGroup
   :members: start, stop, close

Channels
--------

.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.AIVoltage
.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.AICurrent
.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.AIThermocouple
.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.AIRtd
.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.AOVoltage
.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.AOCurrent
.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.CICountEdges
.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.COPulseFreq
.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.DigitalIn
.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.DigitalOut

Timing and triggers
-------------------

.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.ClockSettings
.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.ImplicitTiming
.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.ChangeDetectionSettings
.. autofunction:: pymodaq_plugins_daqmx.hardware.national_instruments.api.counter_output_terminal
.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.DigitalEdgeTrigger
.. autoclass:: pymodaq_plugins_daqmx.hardware.national_instruments.api.AnalogEdgeTrigger
