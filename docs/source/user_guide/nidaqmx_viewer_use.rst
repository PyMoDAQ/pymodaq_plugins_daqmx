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
   group yet (``Dev1/ai0``, ``cDAQ1Mod1/ai0``...). Each one is added as a group named after it, with the first type
   its device can measure (``voltage``, then ``current``, ``thermocouple`` and ``rtd``) and its default parameters; a
   voltage channel gets the widest voltage range of the device.
3. **Choose the type of each channel** (``voltage``, ``current``, ``thermocouple``, ``rtd``). The group is rebuilt with
   only the parameters of the new type; the values that the two types share, such as the range, are kept.
   Remove a channel with the remove button of its group.
4. **Set the acquisition**: the display, the frequency and, for the traces, the number of samples (see below).
5. **Grab or start the live mode.** The task is built from the channels when the first one is available, and rebuilt
   at the next grab when the channels changed (in live mode, at the next start).

The channels are acquired by one task for each module (the device their name starts with, ``cDAQ1Mod1`` for
``cDAQ1Mod1/ai0``), because the modules of a chassis cannot always share a clock (the delta-sigma modules such as the
NI 9211 and NI 9217 cannot be timed with others). Each task gives its own data, named ``NI AI <module>`` (``NI AI cDAQ1Mod1``), and the tasks
start one after the other, without any alignment of their samples. A common clock or start trigger (see below) is
the way to align them when the hardware allows it. The driver refuses to put in one task modules that cannot share a clock
(error -201425, which the plugin turns into a message naming the devices): the generic viewer avoids it, as each
module has its own task.

In each data the channels follow the order of the channels in the group, and are labelled with their names.

Settings
--------

* **Display type**: ``0D`` gives the mean of the samples of each channel (with its standard error), ``1D`` gives the
  trace as a function of time.
* **Frequency Acq.**: the sampling rate that a module starts with.
* **Modules**: one group for each module of the channels (they appear and disappear with the channels), as a module
  can need a rate, a clock and a start of its own. Each module is acquired by its own task, with:

  * **Frequency**: the sampling rate of the module. With an external clock it is the highest frequency that clock
    can have (the driver needs it to size its buffer), not the real one.
  * **Clock**: ``internal`` (the module times itself), a terminal wired to the device (``/Dev1/PFI1``), or the clock
    exported by another module (``/Dev1/ai/SampleClock``), which makes the modules share one clock. Any module may
    follow an external clock. A module cannot be offered its own clock.
  * **Start trigger**: ``none`` (the task starts at once), ``digital edge`` (a *Terminal* such as ``/Dev1/PFI0``, or
    the start trigger exported by another module, and an *Edge*) or ``analog edge`` (a *Channel*, a *Level* in volts
    and an *Edge*). An analog trigger watches one of the channels of the module, which the driver requires to be a
    channel of the task (set its ``read`` box off if you do not want its samples); the list also offers the dedicated
    analog trigger terminals (``/Dev1/APFI0``) of the module, if it has some: such a terminal is not acquired.

  The tasks start in the order that their sources require: a module that waits for the clock or the trigger of another
  one starts first and the one that provides the signal starts last. Two modules that wait for each other cannot be
  started: the plugin says so, and one of them has to use its own clock.
  With an external clock the time between samples is not known, so the 1D axis is the sample index (no unit) and not
  the time in seconds.
* **Nsamples** (``1D`` only): the length of the trace. In ``0D`` the number of points averaged is the *Naverage* of the
  viewer, and in ``1D`` *Naverage* is the number of traces averaged. The driver needs at least two samples for a
  clocked acquisition: *Nsamples* cannot be below 2, and with *Naverage* = 1 two samples are acquired and the first
  one is kept.
* **Channels**: the group described above. Each channel has a ``read`` box (checked by default): unchecked, the
  channel stays in the task but its samples are not in the data, which is what an analog trigger on that channel needs.
  A module whose channels are all unchecked gives no data. The parameters of a channel are the fields of its channel class of the
  API (``AIVoltage``, ``AICurrent``, ``AIThermocouple``, ``AIRtd``), with the same names (the range, ``min_val`` and ``max_val``, is shown in the unit of its quantity: V, A or the temperature units). Changing the type of a channel keeps the values that still make sense: the range is kept only between types that measure the same quantity (thermocouple and RTD), and takes the default of the new type otherwise; see :doc:`config_files`
  for the list.

Loading and saving a configuration
----------------------------------

Entering the channels again at each start is tedious, and the state manager of the Dashboard cannot restore them,
because they exist only once the plugin has started. The way to restore them is to **load a configuration file**
(:doc:`config_files`), which describes the channels of a setup: it is a form of state manager built into the plugin
and dedicated to DAQmx.

The parameters below are in the ``NIDAQmx config`` group of the settings.

* **Configuration**: a drop-down list with ``(manual)`` (the channels are the ones you add) and the configuration
  files of the folder, ``default`` being ``config_daqmx.toml``. As it is a plain parameter, the choice is saved by
  the state manager of the Dashboard, which sets the menu again, and so loads the same file. The list is read
  when the plugin starts, and again after a save.
* **Configuration** also loads the channels: choosing a file replaces the channels of the tree by the ones of the
  file, in the order of the file (which is the order of the data), the frequency, the clock and the start trigger of each module
  (internal clock and no trigger if the file has none). You can then add, remove or change channels as
  usual, also from several devices: the file is only read, never changed, unless you save. One file is one
  configuration: to work with another set of channels, save it under another suffix.
* As soon as the tree is not what the file describes any more (a channel added, removed or changed, a frequency, a clock or
  a trigger modified), the menu goes back to ``(manual)``, so that it never shows a configuration that is not in the tree. To get the
  file back, choose it again in the menu.
* **Save as...**: a button with a LED. A click opens a small dialog asking the *Suffix* of the file
  (``config_daqmx_<suffix>.toml``; ``default`` is the file without suffix), proposed with the configuration loaded.
  The file then describes exactly the channels of the tree, the frequency, the clock and the start trigger of each module
  (those of an existing file that are not in the tree are
  removed). The format of the file groups the channels by module, so each channel is written in the module its name
  starts with (``Dev1`` for ``Dev1/ai1``, ``cDAQ1Mod3`` for ``cDAQ1Mod3/ai0``): channels of several devices can be
  mixed. Only the suffix is given, never a path: the file always goes to the folder of the configuration files. After a save the menu shows the file that was just written, which is what the tree now is. The LED of the button
  is grey until you save, green once the file is written, and orange if it failed.

The loading is done as soon as the choice is made, whether it comes from you or from the state manager. The
status LED of the viewer tells how it went: it shows an error, with the message, when the file cannot be read or
written, and is back to normal when it worked. After a failure the menu goes back to the configuration that is really loaded, so that it never shows something
that is not in the tree.

A file that cannot be read gives an error that names the file and the entry that is wrong.
