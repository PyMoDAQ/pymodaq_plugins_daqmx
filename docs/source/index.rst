.. pymodaq_plugins_daqmx documentation master file, created by
   sphinx-quickstart on Thu Sep 14 15:41:39 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pymodaq_plugins_daqmx's documentation!
=================================================

This PyMoDAQ plugin is devoted to the National Instrument signal acquisition and generation using the NiDAQmx library. It contains generic objects which should be used as a basis to build actuators and viewers performing custom signal acquisition and generation.
In addition, and they are also meant as examples, it provides actuator plugins which can be used to move piezo scanners using the analog output functions of NI acquisition cards, as well as a 0D viewer corresponding to a single photon counter.

This documentation is written as a tutorial to guide you when setting up your NI acquisition devices with PyMoDAQ.

This plugin is compatible with PymoDAQ 4.

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   introduction	 
   user_guide
   creating_plugin
   
