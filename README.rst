pymodaq_plugins_daqmx (National Instrument DAQmx)
#################################################

.. image:: https://img.shields.io/pypi/v/pymodaq_plugins_daqmx.svg
   :target: https://pypi.org/project/pymodaq_plugins_daqmx/
   :alt: Latest Version

.. image:: https://readthedocs.org/projects/pymodaq/badge/?version=latest
   :target: https://pymodaq.readthedocs.io/en/stable/?badge=latest
   :alt: Documentation Status

.. image:: https://github.com/PyMoDAQ/pymodaq_plugins_daqmx/workflows/Upload%20Python%20Package/badge.svg
    :target: https://github.com/PyMoDAQ/pymodaq_plugins_daqmx

Plugins devoted to National Instruments signal acquisition and generation, using the NI-DAQmx driver through the
``nidaqmx`` package of National Instruments (`documentation <https://nidaqmx-python.readthedocs.io/en/stable/>`_):
general actuator and viewers configured from the settings tree, and ready-to-use plugins for analog inputs, counting
and ramps on an analog output.

Authors
=======

* Sébastien J. Weber

Contributors
============

* Amelie Jarnac
* Aurore Finco
* Sébastien Guerrero  (sebastien.guerrero@insa-lyon.fr)
* Cyril Auclair (cyril.auclair@insa-lyon.fr)

Instruments
===========
Below is the list of instruments included in this plugin

Actuators
+++++++++

* **NIDAQmx**: General generation (voltage / current) with National Instrument materials
* **NIDAQmx_RampOutput**: A quantity driven by an analog output, changed by voltage ramps timed by a counter used as a
  clock (value = voltage x conversion factor); several axes (x, y, z) can share the clock

Viewer0D
++++++++

* **NIDAQmx**: General measurement with National Instrument materials (one value per channel and per acquisition)
* **DAQmxAI**: One analog input, as a mean value (0D) or a trace (1D)
* **DAQmxDualAI**: Two analog inputs acquired together, as mean values (0D) or traces (1D)
* **DAQmx_Counter**: Rate of the edges received on a counter input, in counts per second

Viewer1D
++++++++

* **NIDAQmx**: General measurement with National Instrument materials, acquired in the hardware buffer

Requirements
============

* PyMoDAQ >= 5.3.2
* The NI-DAQmx driver of National Instruments, installed on the computer connected to the device (use NI MAX to test
  your hardware). Where the driver cannot be found, the plugins are importable but list no device.
* The ``nidaqmx`` Python package, installed with the plugin.

Status
======

* The general ``NIDAQmx`` viewers were tested with a cDAQ-9174 and a USB-6341 (modules NI-9205, NI-9211, NI-9217).
* The general ``NIDAQmx`` actuator is not finished yet: its movements still raise ``NotImplementedError``.
* ``DAQmxAI``, ``DAQmxDualAI``, ``DAQmx_Counter`` and ``NIDAQmx_RampOutput`` were ported from the ``pydaqmx`` branch
  and are tested against a fake of the ``nidaqmx`` layer only, not yet on hardware.

Documentation
=============

Refer to the `documentation <https://pymodaq.github.io/pymodaq_plugins_daqmx/>`_ to use this plugin or discover its
functionalities.

Build your own plugin
=====================

The ``NIDAQmx`` object (``hardware/national_instruments/daqmxni.py``) wraps the ``nidaqmx`` package: it describes
channels (``AIChannel``, ``AOChannel``, ``CIChannel``, ``ClockCounter``...), builds the task and gives access to it.
``DAQmxAI`` (``NIDAQmx_AI.py``), ``DAQmx_Counter`` and ``NIDAQmx_RampOutput`` (``ramp_output.py``) are small examples
of plugins built on it.

The two branches of the repository
==================================

The repository has two lines of plugins, using two different Python interfaces to the same NI-DAQmx driver:

* ``5.3.x`` (this branch): ``nidaqmx``, the package of National Instruments. This is the one to use and to contribute
  to.
* ``pydaqmx``: `PyDAQmx <https://pythonhosted.org/PyDAQmx/>`_ (``DAQmx`` object in
  ``hardware/national_instruments/daqmx.py`` of that branch). It is frozen and kept for the users of ``PyDAQmx``
  (also the 1.1.x releases). Its generic ``DAQmx`` plugins have no equivalent here: use the ``NIDAQmx`` ones.
