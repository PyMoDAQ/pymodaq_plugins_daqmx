from pymodaq_plugins_daqmx.hardware.national_instruments.daq_NIDAQmx import DAQ_NIDAQmx_Viewer
from pymodaq.control_modules.viewer_utility_classes import main



class DAQ_0DViewer_DAQmx(DAQ_NIDAQmx_Viewer):
    """
        ==================== ========================
        **Attributes**         **Type**
        *data_grabed_signal*   instance of Signal
        *params*               dictionnary list
        *task*
        ==================== ========================

        See Also
        --------
        refresh_hardware
    """
    control_type = "0D"  # could be "0D", "1D"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, control_type=self.control_type, **kwargs)


if __name__ == '__main__':
    main(__file__, False)
