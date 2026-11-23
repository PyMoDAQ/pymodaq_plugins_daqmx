Configuration files
===================

A configuration file describes the channels of the modules of a bench, so that you do not have to enter them again
each time a plugin starts. It is a TOML file, and it works as a state manager built into the plugin and dedicated to
DAQmx: the state manager of the Dashboard cannot restore the channels of a plugin, which exist only once it has
started, whereas a configuration describes them. Each file is a *configuration*, and the plugin offers the list of the
configurations in a drop-down menu, so that the choice is saved with the preset of the plugin.

Where the files are
-------------------

All the files live in the ``daqmx`` folder of the PyMoDAQ **system** configuration folder (for instance
``C:\ProgramData\.pymodaq\daqmx`` on Windows), so that every user of the computer sees the same configurations. A
configuration is named by its *suffix*: ``config_daqmx_<suffix>.toml`` is the configuration ``<suffix>``, and
``config_daqmx.toml`` is the configuration shown as ``default``. When you save a configuration from the plugin, you
give the suffix only.

Example
-------

.. literalinclude:: ../examples/config_daqmx_example.toml
   :language: toml

Format
------

``version``
   Required. The version of the format, ``1``. Another value is refused.

``description``
   Free text.

``[devices.<name>]``
   Optional, one table for each device (a cDAQ chassis for instance). ``product`` is its product type, which is
   informative.

``[modules.<name>]``
   One table for each module, named as in NI MAX (``cDAQ1Mod3``, or ``Dev1`` for a board). The name of a channel is
   its module and its key: ``[modules.cDAQ1Mod3.ai.ai0]`` is the channel ``cDAQ1Mod3/ai0``, so the module of a channel
   is the device its name starts with. ``product`` is the product
   type of the module, informative. ``frequency`` is optional: the sampling frequency of the module in Hz, a positive
   integer. The generic viewer acquires each module with its own task, so each has its own frequency.

``[trigger]``
   Optional: what starts the tasks. A digital trigger starts the task of every module; an analog one watches a channel of
   the file and starts only the task of its module. ``type`` is ``digital edge`` (``terminal``, such as
   ``/cDAQ1/PFI0``, and ``edge``) or ``analog edge`` (``channel``, such as ``cDAQ1Mod3/ai0``, ``level`` in volts
   and ``edge``). ``edge`` is ``rising`` (the default) or ``falling``. Without this table the tasks start at once.

``[modules.<name>.ai.<key>]``
   One table for each analog input channel. The channel is ``<module>/<key>`` (``cDAQ1Mod3/ai0``) and the order of
   the tables in the file is the order of the data of an acquisition. ``type`` selects the kind of channel and its
   other keys. ``info`` is a free note, kept when the file is saved again. A key that does not belong to the type
   is an error, so that a typo cannot go unnoticed.

The names of the keys are the names of the arguments of the channels of the Python API
(see :doc:`../api/reference`), and a value that is a constant of the driver is written with its name.

.. list-table:: Analog input channels
   :header-rows: 1

   * - ``type``
     - Key
     - Value
     - Default
   * - ``voltage``
     - ``min_val``, ``max_val``
     - Volts, ``min_val`` < ``max_val``
     - -10, 10
   * -
     - ``terminal_config``
     - ``RSE``, ``NRSE``, ``DIFF``, ``PSEUDO_DIFF``, ``DEFAULT``
     - ``DEFAULT``
   * - ``current``
     - ``min_val``, ``max_val``
     - Amperes, ``min_val`` < ``max_val``
     - -0.02, 0.02
   * -
     - ``terminal_config``
     - same as ``voltage``
     - ``DEFAULT``
   * - ``thermocouple``
     - ``thermocouple_type``
     - ``J``, ``K``, ``N``, ``R``, ``S``, ``T``, ``B``, ``E``, ``A``, ``C``
     - ``K``
   * -
     - ``units``
     - ``DEG_C``, ``DEG_F``, ``K``, ``DEG_R``, ``FROM_CUSTOM_SCALE``
     - ``DEG_C``
   * -
     - ``min_val``, ``max_val``
     - In ``units``, ``min_val`` < ``max_val``
     - 0, 100
   * - ``rtd``
     - ``rtd_type``
     - ``PT_3750``, ``PT_3851``, ``PT_3911``, ``PT_3916``, ``PT_3920``, ``PT_3928``, ``CUSTOM``
     - ``PT_3851``
   * -
     - ``resistance_config``
     - ``TWO_WIRE``, ``THREE_WIRE``, ``FOUR_WIRE``
     - ``THREE_WIRE``
   * -
     - ``excitation_current``
     - Amperes, positive
     - 0.0025
   * -
     - ``r_0``
     - Ohms at 0 °C
     - 100
   * -
     - ``units``, ``min_val``, ``max_val``
     - as ``thermocouple``
     - ``DEG_C``, 0, 100

Only the analog input channels are described for now.

Default values
--------------

Only ``type`` is required in a channel. **A key you leave out takes the default value of the table above, which is the
default of the Python API**, and nothing tells you when it happens. In particular, a voltage channel without
``min_val`` and ``max_val`` is measured on the range -10 V to 10 V, and a thermocouple channel without them on 0 to
100 degrees. The range is passed to the driver, which may round it to a range the module supports, so write the
ranges you rely on explicitly:

.. code-block:: toml

   [modules.cDAQ1Mod3.ai.ai0]
   type = "voltage"        # measured from -10 V to 10 V, RSE not set: DEFAULT terminal configuration

   [modules.cDAQ1Mod3.ai.ai1]
   type = "voltage"
   min_val = -1.0          # explicit, nothing is left to the defaults
   max_val = 1.0
   terminal_config = "RSE"

``terminal_config = "DEFAULT"`` lets the driver choose the terminal configuration of the module. The settings tree of
the plugin shows the values that were read, defaults included, once a configuration is chosen.

Mistakes
--------

A file the plugin cannot use is refused with a message that names the file and the entry, for instance::

   config_daqmx.toml: [cDAQ1Mod3.ai.ai0] unknown terminal_config 'FLOATING', expected one of ['DEFAULT', 'RSE', ...]

Files of the previous versions
------------------------------

The files of the previous versions of the plugin (a ``NIDAQ_Devices`` table with ``DEVICE01`` and ``MODULE01``
tables) can still be read, with their voltage, current and thermocouple channels. Choosing such a file and saving it
under a new suffix writes it in the current format; the original is never modified. The keys were renamed:
``value_min`` and ``value_max`` became ``min_val`` and ``max_val``, ``termination`` became ``terminal_config``, and
``thermo_type`` became ``thermocouple_type``. The keys ``source`` and ``analog_type`` are replaced by ``type``.
