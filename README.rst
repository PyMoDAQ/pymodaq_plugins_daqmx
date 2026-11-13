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
``nidaqmx`` package of National Instruments (`documentation <https://nidaqmx-python.readthedocs.io/en/stable/>`_).
They include a ``NIDAQmx`` actuator for signal generation, a 0D viewer for quick measurements and a 1D viewer for data
acquisition as a function of time, and the ``NIDAQmx`` object (``hardware/national_instruments/daqmxni.py``) to build
your own plugin on.

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
  clock (nm = V x conversion factor); several axes (x, y, z) can share the clock

Viewer0D
++++++++

* **NIDAQmx**: General measurement with National Instrument materials (one value per channel and per acquisition)
* **DAQmxAI**: One analog input, as a mean value (0D) or a trace (1D)
* **DAQmxDualAI**: Two analog inputs acquired together, as mean values (0D) or traces (1D)
* **DAQmx_Counter**: Rate of the edges received on a counter input, in counts per second

Viewer1D
++++++++

* **NIDAQmx**: General measurement with National Instrument materials, acquired in the hardware buffer

Documentation
+++++++++++++

Refer to the `documentation <https://pymodaq.github.io/pymodaq_plugins_daqmx/>`_ to use this plugin or discover its functionalities.

Difference with the pydaqmx branch
==================================

The repository has two lines of plugins, which use two different Python interfaces to the same NI-DAQmx driver. They
do not share their instrument plugins (``NIDAQmx`` here, ``DAQmx_...`` there).

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * -
     - ``5.3.x`` branch (this one)
     - ``pydaqmx`` branch
   * - Python interface
     - `nidaqmx <https://nidaqmx-python.readthedocs.io/en/stable/>`_, the package of National Instruments
       (``NIDAQmx`` object in ``daqmxni.py``)
     - `PyDAQmx <https://pythonhosted.org/PyDAQmx/>`_ (``DAQmx`` object in ``hardware/national_instruments/daqmx.py`` of that branch)
   * - Instruments
     - ``NIDAQmx`` actuator, 0D viewer and 1D viewer, ``DAQmxAI``, ``DAQmxDualAI``, ``DAQmx_Counter``,
       ``NIDAQmx_RampOutput``
     - generic ``DAQmx`` actuator and viewers (0D, 1D), ``DAQmxAI``, ``DAQmxDualAI``, ``DAQmx_PLcounter``,
       ``DAQmx_ScannerControl``, ``DAQmx_MultipleScannerControl``
   * - Use
     - measurement of voltage, current or temperature with a general viewer, whose channels can be loaded from a
       configuration file of the user (``config_daqmx.toml``) and saved from the interface; specific tasks (analog
       input, counting, ramps on an analog output) in dedicated plugins
     - the same specific tasks (``DAQmx_PLcounter`` and the scanner controls are the former names of ``DAQmx_Counter``
       and ``NIDAQmx_RampOutput``) and a base to write your own plugin
   * - State
     - the ``NIDAQmx`` viewers were tested with a cDAQ-9174 and a USB-6341 (modules NI-9205, NI-9211, NI-9217); the
       ``DAQmxAI``, ``DAQmxDualAI``, ``DAQmx_Counter`` and ``NIDAQmx_RampOutput`` plugins were ported from the
       ``pydaqmx`` branch and tested against a fake of the ``nidaqmx`` layer only, not yet on hardware; the
       ``NIDAQmx`` actuator is not finished yet (its movements still raise ``NotImplementedError``)
     - the ``PyDAQmx`` based plugins, kept as they are (frozen: new developments go to this ``5.3.x`` branch)

This branch does not contain the ``PyDAQmx`` based ``DAQmx`` object (``daqmx.py``, ``daqmx_objects.py``) nor the
instrument plugins of the ``pydaqmx`` branch: use that branch (or the 1.1.x releases) if you need them. The
user guides of the photon counter and the scanner control remain here as a reference, they describe those deprecated
plugins.

Requirements
============

* PyMoDAQ >= 5.3.7
* the NI-DAQmx driver of National Instruments, installed on the computer connected to the device (use NI MAX to test
  your hardware). Where the driver cannot be found, the modules of this plugin are not usable and PyMoDAQ skips them.
* the ``nidaqmx`` Python package, installed with the plugin.
