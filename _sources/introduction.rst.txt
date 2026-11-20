Introduction
============

.. _introduction:

NI acquisition and signal generation devices are very versatile instruments, which can be used both as actuators and detectors. They offer the possibility to generate or acquire both analog and digital signals, with external or internal timing of the tasks. As a consequence, one can hardly provide a generic PyMoDAQ plugin to operate a NI acquisition card, and you will most probably need to build your own module to perform the precise task that you have in mind. However, if your goal is to perform basics analog measurement, you can begin with the nidaqmx viewer which enable acquisition of various physical quantity.

Installation
------------

Of course, you need a working PyMoDAQ installation, see `here <http://pymodaq.cnrs.fr/en/latest/quick_start.html#>`_ the installation procedure. You also need to have the NIDAQmx driver on your computer, together with the acquisition device. Use the NI MAX software to test your hardware.

Then you can install the *pymodaq_plugins_daqmx* module, from the `plugin manager <http://pymodaq.cnrs.fr/en/latest/user_folder/plugin_manager.html>`_ or with ``pip install pymodaq_plugins_daqmx``.
The interface between the NIDAQmx driver and python (and thus PyMoDAQ) is done by the package `NIDAQmx <https://nidaqmx-python.readthedocs.io/en/stable/>`_.

