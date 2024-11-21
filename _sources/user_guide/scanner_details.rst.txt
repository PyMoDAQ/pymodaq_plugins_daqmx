Details about the implementation of the MultipleScannerControl move
===================================================================

Similarly to the case of the PLcounter, we need to use several channels together to make the scanner work, a clock and an analog output. In principle, we can use the same trick as for the PLcounter and define the controller as a dict containing 2 ``DAQmx`` objects. This is what is done in the ScannerControl plugin, but its means that you need one clock channel for each analog output channel, so if you have many scanners, it will very quickly become an issue. In addition, with a scanner, you most probably want to use the Scan extension. For each movement, the extension sends the command to move to every actuator roughly simultaneously: if your scanners share the same clock, you will get into trouble.

Introduction of a new object to use as controller
-------------------------------------------------

The solution proposed with the MultipleScannerControl plugin is to add an additional object to handle the synchronisation of the different scanners. This object is the ``AO_with_clock_DAQmx`` which is defined in the file ``daqmx_objects.py``, which is used as controller instead of the ``DAQmx``. 

The ``AO_with_clock_DAQmx`` has 2 attributes, ``clock`` and ``analog`` which are ``DAQmx`` objects, each of them containing, as usual, a single task.

The clock will thus be shared by all the scanners connected to the ``AO_with_clock_DAQmx`` controller. The parameters of the clock can thus only be modified in the settings of the Master scanner.

The analog DAQmx object has an AnalogOutput task with several output channels, one for each scanner. The list of these channels is stored in the attribute ``AOchannels`` As a result, the list of positions sent by each scanner plugins to describe the movement have to be reformatted, as values have to be sent to all the channels. For exemple, to move the X scanner from 1 to 5 µm in steps of 1 µm, the plugins sends the list ``[1000, 2000, 3000, 4000, 5000]``, but if a Y scanner is also connected to the ``AO_with_clock_DAQmx``, it needs to be reformatted to ``[[1000, 2000, 3000, 4000, 5000], [current_Y_position, current_Y_position, current_Y_position, current_Y_position, current_Y_position]]``. This reformatting is done by the ``AO_with_clock_DAQmx`` controller.

Handling of the timing
----------------------

Having a single controller object allows performing the movements of each scanners one after the other, without conflicts in the use of the clock counters by the different scanners. This is achieved by locking the ``AO_with_clock_DAQmx`` controller during the movement of any scanner. When a move command is sent, the ``locked`` attribute of the controller is set to ``True``.
As long as this variable is set to ``True``, no other movement is started. If another scanner gets a command for moving, then it is set to a waiting state (the attribute ``waiting_to_move`` from the scanner plugin is set to ``True``) until the signal ``ni_card_ready_for_moving`` is received from the controller indicating that the movement can resume.

When the movement is over, the scanner plugin received a ``move_done_signal`` from PymoDAQ, which is emitted when the current position is close enough to the current position. This signal is connected to the ``AO_with_clock_DAQmx`` controller, which switches to the unlocked state (``locked`` attribute set back to ``False``) and emits the signal ``ni_card_ready_for_moving``. 


Reading the scanner position
----------------------------
Another issue with using a NI card to pilot a piezo scanner is that **one cannot read the current voltage applied at an analog output.** In order to know the current position of the scanner, the solution used here is to **get the current index of the clock** from the NI card, and then display the corresponding position in the list that was sent to the device. 

As a consequence, the position is set to 1 nm when restarting the plugin, as the current position cannot be read from the hardware. This might cause quick movements, so be careful to go back to zero before closing the plugin. 
