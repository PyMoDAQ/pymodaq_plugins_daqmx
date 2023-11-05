Using the 0D viewer PLcounter
=============================

This plugin is meant to be used to count single photons with a NI card. The signal consists of TTL pulses sent by a detector (mainly an avalanche photodiode (APD)).

The signal is displayed in kcounts/s.

It was tested only with NI PCIe 63XX devices.

Configuration
-------------

You need to provide 4 parameters, as shown in the screenshot below.

* **Counting channel**: the internal counting channel that you will use to count the rising edges of the signal, something like ``Dev[X]/ctr[Y]``
  
* **Photon source**: the channel on which you send the signal from the APD, something like ``/Dev[X]/PFI[Y]``, to choose from a given list.

* **Clock frequency**: the acquisition rate, each data point corresponds to counting during the associated time interval. 

* **Clock channel**: the channel which you will use for measurement timing, something like ``Dev[X]/ctr[Y]``. You cannot use the same as for the counting channel!

  .. image:: /images/PLcounter.png
    :width: 800

This plugin is not intended to be used with a "Slave" configuration, but you can definitely use the same NI card device as hardware for other plugins at the same time.

Be careful to use as photon source the default input terminal corresponding to the counting channel, check the documentation of your NI device about this.
	    
	    
Use
---

It works as a usual 0D viewer plugin. It is recommended to start with a snap before launching a continuous grab.

If you need to use one of the counter/clock channels with another plugin, do not forget to stop the measurement, otherwise you will get an error about the resource being busy.

You might get many warnings in the log about the task being stopped before being finished, do not worry about it, the measurement is still fine. If you know how to solve this, please contribute!
