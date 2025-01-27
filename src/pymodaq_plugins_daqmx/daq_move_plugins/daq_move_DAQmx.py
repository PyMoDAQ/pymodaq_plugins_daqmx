from ..hardware.national_instruments.daq_NIDAQmx import DAQ_NIDAQmx_Actuator


class DAQ_Move_DAQmx(DAQ_NIDAQmx_Actuator):
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

