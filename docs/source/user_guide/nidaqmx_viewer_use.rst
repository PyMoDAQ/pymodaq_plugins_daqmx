Generic viewer NIDAQmx
======================

``NIDAQmx`` is the generic viewer for the analog inputs of any NI device (a card, or the modules of a cDAQ). It is
listed with the 0D viewers (``DAQ_0DViewer_NIDAQmx``) and with the 1D viewers (``DAQ_1DViewer_NIDAQmx``): they are the
same plugin, the 1D one only starts with the ``1D`` display. The channels are not fixed in the plugin, you add the ones
you need, each with the parameters of its type.

.. note::
    Stay aware of the maximum quantity measurable, which depends on what your device supports. The plugin has been
    tested against a fake of the ``nidaqmx`` layer, and still needs tests on hardware.

How to use it
-------------

1. **Initialize the detector first.** The list of the channels of the computer is read by the plugin when it starts,
   so the *Add* button of the ``Channels`` group has nothing to offer before the initialization. The plugin
   initializes without any channel (there is nothing to configure yet) and a grab without a channel only writes
   *No channel to acquire* in the log.
2. **Add the channels.** The *Add* button of ``Channels`` lists the channels of the computer that are not in the
   group yet (``Dev1/ai0``, ``cDAQ1Mod1/ai0``...). Each one is added as a group named after it, with the type
   ``voltage`` and its default parameters.
3. **Choose the type of each channel** (``voltage``, ``current``, ``thermocouple``, ``rtd``). The group is rebuilt with
   only the parameters of the new type; the values that the two types share, such as the range, are kept.
   Remove a channel with the remove button of its group.
4. **Set the acquisition**: the display, the frequency and, for the traces, the number of samples (see below).
5. **Grab or start the live mode.** The task is built from the channels when the first one is available, and rebuilt
   at the next grab when the channels changed (in live mode, at the next start).

The data follow the order of the channels in the group, and are labelled with their names.

Settings
--------

* **Display type**: ``0D`` gives the mean of the samples of each channel (with its standard error), ``1D`` gives the
  trace as a function of time.
* **Frequency Acq.**: the sampling rate, common to all the channels.
* **Nsamples** (``1D`` only): the length of the trace. In ``0D`` the number of points averaged is the *Naverage* of the
  viewer, and in ``1D`` *Naverage* is the number of traces averaged. The driver needs at least two samples for a
  clocked acquisition: *Nsamples* cannot be below 2, and with *Naverage* = 1 two samples are acquired and the first
  one is kept.
* **Channels**: the group described above. The parameters of a channel are the fields of its channel class of the
  API (``AIVoltage``, ``AICurrent``, ``AIThermocouple``, ``AIRtd``), with the same names; see :doc:`config_files`
  for the list.

Loading and saving a configuration
----------------------------------

Entering the channels again at each start is tedious, and the state manager of the Dashboard cannot restore them,
because they exist only once the plugin has started. The way to restore them is to **load a configuration file**
(:doc:`config_files`), which describes the channels of a setup: it is a form of state manager built into the plugin
and dedicated to DAQmx.

The three parameters below are in the ``NIDAQmx config`` group of the settings.

* **Configuration**: a drop-down list with ``(manual)`` (the channels are the ones you add) and the configuration
  files of the folder, ``default`` being ``config_daqmx.toml``. As it is a plain parameter, the choice is saved by
  the state manager of the Dashboard, which sets the menu again, and so loads the same file. The list is read
  when the plugin starts, and again after a save.
* **Module**: ``(all)``, the default, or one of the modules of the chosen file. Choosing a configuration loads the
  channels of all its modules, in the order of the file (which is the order of the data); choosing a module loads only
  its channels. You can then add, remove or change channels as usual, also from several devices: the file is only
  read, never changed, unless you save.
* **Save as...**: a button with a LED. A click opens a small dialog asking the *Suffix* of the file
  (``config_daqmx_<suffix>.toml``; ``default`` is the file without suffix), proposed with the configuration loaded.
  The channels of the tree are written in that file, each one in the module its name starts with (``Dev1`` for
  ``Dev1/ai1``, ``cDAQ1Mod3`` for ``cDAQ1Mod3/ai0``), so that channels of several devices can be mixed. In an existing
  file the modules of the tree are replaced and the other ones are kept. Only the suffix is given, never a path: the
  file always goes to the folder of the configuration files. The LED of the button is grey until you save, green once
  the file is written, and orange if it failed.

The loading is done as soon as the choice is made, whether it comes from you or from the state manager. The
status LED of the viewer tells how it went: it shows an error, with the message, when the file cannot be read or
written, and is back to normal when it worked. After a failure the menus go back to the configuration and module that are really
loaded, so that they never show something that is not in the tree.

A file that cannot be read gives an error that names the file and the entry that is wrong.
