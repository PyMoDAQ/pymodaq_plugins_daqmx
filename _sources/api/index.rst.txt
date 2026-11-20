Python API
==========

Besides the PyMoDAQ plugins, this package offers a Python API to describe and run NI-DAQmx tasks from any code: your
own plugin, a PyMoDAQ extension, or a plain script. It lives in
``pymodaq_plugins_daqmx.hardware.national_instruments.api``, wraps the ``nidaqmx`` package of National Instruments and
**imports neither Qt nor PyMoDAQ**, so a script can use it without a graphical environment.

.. code-block:: python

   from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
       AIVoltage, AnalogInputTask, ClockSettings, TaskConfig)

   config = TaskConfig(channels=[AIVoltage('Dev1/ai0'), AIVoltage('Dev1/ai1')],
                       timing=ClockSettings(rate=10_000., samples=1000))
   with AnalogInputTask(config) as task:
       task.start()
       data = task.read_analog()      # float64 array shaped (2, 1000)
       task.stop()

The idea in one sentence: **describe** the task with small immutable objects, **hand** the description to a typed
task, then ``start``, ``read`` or ``write`` and ``close``.

.. toctree::
   :maxdepth: 2

   concepts
   examples
   reference
   migration

Stability
---------

The names listed in ``api.__all__`` are the public API. They only change in a new major version of the plugin, and
the changes are listed in the migration page. Anything else (the ``_Task`` base class, the modules themselves) is
internal.

How it is tested
----------------

The tests replace the ``nidaqmx`` package by a double that behaves like the one recorded on NI MAX simulated devices
by ``tests/contract/contract_check.py`` (shapes returned by ``read``, error codes, callback threads...). The
reports of the real driver are kept in ``tests/contract/reports``. The examples of this documentation are run by the
tests too. You can run the same script on your own hardware: its README says how.
