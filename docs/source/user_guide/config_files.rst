Configuration files
===================

A configuration file describes the channels of the modules of a bench, so that you do not have to enter them again
each time a plugin starts. It is a TOML file. Each file is a *configuration*, and the plugin offers the list of the
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
   One table for each module, named as in NI MAX (``cDAQ1Mod3``, or ``Dev1`` for a board). ``product`` is the product
   type of the module, informative.

``[modules.<name>.ai.<key>]``
   One table for each analog input channel. The channel is ``<module>/<key>`` (``cDAQ1Mod3/ai0``) and the order of
   the tables in the file is the order of the data of an acquisition. ``type`` selects the kind of channel and its
   other keys. ``info`` is a free note, kept when the file is saved again. A key that does not belong to the type
   is an error, so that a typo cannot go unnoticed. A key you leave out has the default of the API, given below.

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
