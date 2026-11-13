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
`PyDAQmx <https://pythonhosted.org/PyDAQmx/>`_ package. They include generic actuator and viewer plugins (a task
configured from the settings tree), plugins for specific uses (photon counting, piezo scanner control, analog input
acquisition), and the ``DAQmx`` wrapper object to build your own plugin on.

Authors
=======

* Sébastien J. Weber

Contributors
============

* Amelie Jarnac
* Aurore Finco

Instruments
===========
Below is the list of instruments included in this plugin

Actuators
+++++++++

* **DAQmx**: generic signal generation (analog, digital) with a NI device, configured from the settings tree
* **DAQmx_ScannerControl**: control of a piezo scanner with an analog output. It needs a clock channel to time the
  movement and display the position
* **DAQmx_MultipleScannerControl**: control of several piezo scanners (x, y, z) with analog outputs, sharing one clock
  channel between the master and the slave modules

Viewer0D
++++++++

* **DAQmx**: generic signal acquisition with a NI device, configured from the settings tree
* **DAQmxAI**: acquisition of one analog input channel, displayed as 0D or 1D data
* **DAQmxDualAI**: acquisition of two analog input channels, displayed as 0D or 1D data
* **DAQmx_PLcounter**: single photon counting

Viewer1D
++++++++

* **DAQmx**: generic signal acquisition with a NI device as a function of time, configured from the settings tree

Documentation
+++++++++++++

Refer to the `documentation <https://pymodaq.github.io/pymodaq_plugins_daqmx/>`_ to use this plugin or discover its
functionalities (user guide for the photon counter and the scanner control, and how to create your own module with
the ``DAQmx`` object).

Difference with the 5.3.x branch
================================

The repository has two lines of plugins, which use two different Python interfaces to the same NI-DAQmx driver. They
do not share their instrument plugins (``DAQmx_...`` here, ``NIDAQmx`` there).

**This branch is frozen**: it is kept for the users of ``PyDAQmx`` and receives no new development. The specific
plugins (analog input, counter, ramp output) have been ported to the ``5.3.x`` branch (``DAQmxAI``, ``DAQmxDualAI``,
``DAQmx_Counter``, ``NIDAQmx_RampOutput``), which is the one to use and to contribute to.

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * -
     - ``pydaqmx`` branch (this one)
     - ``5.3.x`` branch
   * - Python interface
     - `PyDAQmx <https://pythonhosted.org/PyDAQmx/>`_ (``DAQmx`` object in ``hardware/national_instruments/daqmx.py``)
     - `nidaqmx <https://nidaqmx-python.readthedocs.io/en/stable/>`_, the package of National Instruments (``NIDAQmx``
       object in ``daqmxni.py``)
   * - Instruments
     - generic ``DAQmx`` actuator and viewers (0D, 1D), ``DAQmxAI``, ``DAQmxDualAI``, ``DAQmx_PLcounter``,
       ``DAQmx_ScannerControl``, ``DAQmx_MultipleScannerControl``
     - ``NIDAQmx`` actuator, 0D viewer and 1D viewer
   * - Use
     - specific tasks (photon counting, piezo scanner control, analog input) and a base to write your own plugin
     - measurement of voltage, current or temperature with a general viewer, whose channels can be loaded from a
       configuration file of the user (``config_daqmx.toml``) and saved from the interface
   * - State
     - the ``PyDAQmx`` based plugins, kept as they are
     - the ``NIDAQmx`` viewers were tested with a cDAQ-9174 and a USB-6341 (modules NI-9205, NI-9211, NI-9217); the
       ``NIDAQmx`` actuator is not finished yet (its movements still raise ``NotImplementedError``)

The ``5.3.x`` branch still contains the ``PyDAQmx`` based ``DAQmx`` object and its user guides, but not the instrument plugins
of this branch.

Requirements
============

* PyMoDAQ >= 5.3.7
* the NI-DAQmx driver of National Instruments, installed on the computer connected to the device (use NI MAX to test
  your hardware). Where ``PyDAQmx`` cannot find the driver, the modules of this plugin cannot be imported and PyMoDAQ
  skips them.
* the ``pydaqmx`` Python package, installed with the plugin.
