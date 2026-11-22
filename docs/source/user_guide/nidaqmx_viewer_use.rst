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
  viewer, and in ``1D`` *Naverage* is the number of traces averaged.
* **Channels**: the group described above. The parameters of a channel are the fields of its channel class of the
  API (``AIVoltage``, ``AICurrent``, ``AIThermocouple``, ``AIRtd``), with the same names; see :doc:`config_files`
  for the list.

Loading a configuration
-----------------------

Entering the channels again at each start is tedious, and the state manager of the Dashboard cannot restore them,
because they exist only once the plugin has started. The way to restore them is to **load a configuration file**
(:doc:`config_files`), which describes the channels of a setup. This choice, a drop-down list of the configurations
found in the folder of the files, is not available in the viewer yet: it comes in a following version, and until
then the channels have to be added by hand.
