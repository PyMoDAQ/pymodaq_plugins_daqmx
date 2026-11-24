Examples
========

Each example is a complete script. They are run by the tests of the package against a double of the driver, so they
stay correct; on a computer with an NI device, change the device names and run them.

Discover the hardware
---------------------

.. literalinclude:: ../examples/discover_hardware.py
   :language: python

Acquire analog inputs
---------------------

.. literalinclude:: ../examples/analog_input.py
   :language: python

Wait for a trigger
------------------

.. literalinclude:: ../examples/triggered_acquisition.py
   :language: python

Generate analog outputs
-----------------------

.. literalinclude:: ../examples/analog_output.py
   :language: python

Count pulses with a clock
-------------------------

.. literalinclude:: ../examples/counter_rate.py
   :language: python

Be told when samples are ready
------------------------------

.. literalinclude:: ../examples/samples_ready.py
   :language: python
