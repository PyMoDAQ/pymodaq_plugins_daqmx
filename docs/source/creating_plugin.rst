.. _create_plugin:

Creating a plugin for your specific needs
=========================================

In order to create a plugin using a NI card to acquire some data or control an actuator, or even synchronize the acquisition of data with another device, you should start as usual from the `plugin template <https://github.com/PyMoDAQ/pymodaq_plugins_template>`_. It is also strongly recommended that you read the tutorial about instrument plugins `available in the PyMoDAQ documentation <http://pymodaq.cnrs.fr/en/latest/tutorials/plugin_development.html#>`_.

Then you have to analyze the experiment that you want to perform and find the best type of controller that you should use:

* a single ``DAQmx`` object, if you need to perform only one type of task.

* a dict of several ``DAQmx`` objects, like in the PLcounter example, if you will only use the NI card but need to combine several tasks.

* a dict of ``DAQmx`` objects and other hardware controllers, for example if you want to synchronise your acquisition with an actuator which will be triggered by the NI card.

* Another more complicated object (that you will need to write!), like in the MultipleScannerControl example, if you need to share some resources of the NI card between different instrument plugins which control independent parameters/measurments. Beware in particular of the Scan extension which sends all the move commands at the same time.
