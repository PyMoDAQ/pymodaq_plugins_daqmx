User guide
==========

Now that you have a working installation, two options are possible: either there is already a plugin doing exactly what you need, or most probably, you need to build your own daq_move or daq_viewer.
The available specific functions are:

* counting single photons (``DAQmx_PL_counter``). (deprecated)
* using an analog output to move a piezoelectric scanner at a desired (slow) speed (``DAQmx_ScannerControl`` and ``DAQmx_MultipleScannerControl``). (deprecated)
* 0D data visualization & acquisition
* bufferized 1D data visualization & acquisition

This user guide will first explain how to use these plugins, and then detail how they work.

.. toctree::
   :maxdepth: 1
   
   user_guide/counter_use
   user_guide/scanner_use
   user_guide/nidaqmx_viewer_use

For any other use, you will need to create your own move or viewer based on this plugin. See the :ref:`create_plugin` guide for a detailed procedure.
   
Working principle of the plugins
--------------------------------

The controller object, which is usually the wrapper to your hardware, will always be a ``NIDAQmx`` object. These are defined in ``hardware\national_instruments\daqmxni.py``. Such an object contains a **task**, which is configured and then sent to the NI device. Beware that a task can only contain one channel type. The channel types are Analog Output, Analog Input, Digital Output, Digital Input or Counter. As a consequence, if you need to combine several of them, your controller will be a bit more complicated. It might be a dict containing several ``NIDAQmx`` objects, as in the photon counter example, or you might even need to create a specific object to handle these ``NIDAQmx`` objects, as in the scanner control example. More details about these two situations are given in the following sections.

.. toctree::
   :maxdepth: 1
   
   user_guide/counter_details
   user_guide/scanner_details


