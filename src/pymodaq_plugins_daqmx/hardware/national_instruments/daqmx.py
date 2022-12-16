import PyDAQmx
import ctypes
from enum import IntEnum
import numpy as np
from pymodaq.daq_utils.daq_utils import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))


class DAQ_NIDAQ_source(IntEnum):
    """
        Enum class of NIDAQ_source

        =============== ==========
        **Attributes**   **Type**
        *Analog_Input*   int
        *Counter*        int
        =============== ==========
    """
    Analog_Input = 0
    Counter = 1
    Analog_Output = 2
    Digital_Output = 3
    Digital_Input = 4
    Terminals = 5

    @classmethod
    def names(cls):
        return [name for name, member in cls.__members__.items()]


class DAQ_analog_types(IntEnum):
    """
        Enum class of Ai types

        =============== ==========
        **Attributes**   **Type**
        =============== ==========
    """
    Voltage = PyDAQmx.DAQmx_Val_Voltage
    Current = PyDAQmx.DAQmx_Val_Current
    Thermocouple = PyDAQmx.DAQmx_Val_Temp_TC

    @classmethod
    def names(cls):
        return [name for name, member in cls.__members__.items()]

    @classmethod
    def values(cls):
        return [cls[name].value for name, member in cls.__members__.items()]


class DAQ_thermocouples(IntEnum):
    """
        Enum class of thermocouples type

        =============== ==========
        **Attributes**   **Type**
        =============== ==========
    """
    J = PyDAQmx.DAQmx_Val_J_Type_TC
    K = PyDAQmx.DAQmx_Val_K_Type_TC
    N = PyDAQmx.DAQmx_Val_N_Type_TC
    R = PyDAQmx.DAQmx_Val_R_Type_TC
    S = PyDAQmx.DAQmx_Val_S_Type_TC
    T = PyDAQmx.DAQmx_Val_T_Type_TC
    B = PyDAQmx.DAQmx_Val_B_Type_TC
    E = PyDAQmx.DAQmx_Val_E_Type_TC

    @classmethod
    def names(cls):
        return [name for name, member in cls.__members__.items()]


class DAQ_termination(IntEnum):
    """
        Enum class of thermocouples type

        =============== ==========
        **Attributes**   **Type**
        =============== ==========
    """
    Auto = PyDAQmx.DAQmx_Val_Cfg_Default
    RSE = PyDAQmx.DAQmx_Val_RSE
    NRSE = PyDAQmx.DAQmx_Val_NRSE
    Diff = PyDAQmx.DAQmx_Val_Diff
    Pseudodiff = PyDAQmx.DAQmx_Val_PseudoDiff

    @classmethod
    def names(cls):
        return [name for name, member in cls.__members__.items()]


class Edge(IntEnum):
    """
    """
    Rising = PyDAQmx.DAQmx_Val_Rising
    Falling = PyDAQmx.DAQmx_Val_Falling

    @classmethod
    def names(cls):
        return [name for name, member in cls.__members__.items()]


class ClockMode(IntEnum):
    """
    """
    Finite = PyDAQmx.DAQmx_Val_Rising
    Continuous = PyDAQmx.DAQmx_Val_Falling

    @classmethod
    def names(cls):
        return [name for name, member in cls.__members__.items()]


class ClockSettingsBase:
    def __init__(self, Nsamples=1000, repetition=False):

        self.Nsamples = Nsamples
        self.repetition = repetition


class ClockSettings(ClockSettingsBase):
    def __init__(self, source=None, frequency=1000, Nsamples=1000, edge=Edge.names()[0], repetition=False):
        super().__init__(Nsamples, repetition)
        self.source = source
        assert edge in Edge.names()
        self.frequency = frequency
        self.edge = edge


class ChangeDetectionSettings(ClockSettingsBase):
    def __init__(self, Nsamples=1000, rising_channel='', falling_channel='',
                 repetition=False):
        super().__init__(Nsamples, repetition)
        self.rising_channel = rising_channel
        self.falling_channel = falling_channel


class TriggerSettings:
    def __init__(self, trig_source='', enable=False, edge=Edge.names()[0], level=0.1):
        assert edge in Edge.names()
        self.trig_source = trig_source
        self.enable = enable
        self.edge = edge
        self.level = level


class Channel:
    def __init__(self, name='', source=DAQ_NIDAQ_source.names()[0]):
        """
        Parameters
        ----------

        """
        self.name = name
        assert source in DAQ_NIDAQ_source.names()
        self.source = source


class AChannel(Channel):
    def __init__(self, analog_type=DAQ_analog_types.names()[0], value_min=-10., value_max=+10., **kwargs):
        """
        Parameters
        ----------
        min: (float) minimum value for the configured input channel (could be voltage, amps, temperature...)
        max: (float) maximum value for the configured input channel
        """
        super().__init__(**kwargs)
        self.value_min = value_min
        self.value_max = value_max
        self.analog_type = analog_type


class AIChannel(AChannel):
    def __init__(self, termination=DAQ_termination.names()[0], **kwargs):
        super().__init__(**kwargs)
        assert termination in DAQ_termination.names()
        self.termination = termination


class AIThermoChannel(AIChannel):
    def __init__(self, thermo_type=DAQ_thermocouples.names()[0], **kwargs):
        super().__init__(**kwargs)
        assert thermo_type in DAQ_thermocouples.names()
        self.thermo_type = thermo_type


class AOChannel(AChannel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Counter(Channel):
    def __init__(self, edge=Edge.names()[0], counter_type="Edge counter", **kwargs):
        assert edge in Edge.names()
        super().__init__(**kwargs)
        self.edge = edge
        # counter_type options are Edge Counter, Clock Output and SemiPeriod Input
        self.counter_type = counter_type
        if kwargs.get("clock_frequency"):
            self.clock_frequency = kwargs["clock_frequency"]
        if kwargs.get("clock_frequency"):
            self.value_max = kwargs["value_max"]


class DigitalChannel(Channel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class DOChannel(DigitalChannel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class DIChannel(DigitalChannel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


def try_string_buffer(fun, *args):
    """
    generic function to read string from a PyDAQmx function making sure the chosen buffer is large enough
    Parameters
    ----------
    fun: (PyDAQmx function pointer) e.g. PyDAQmx.DAQmxGetSysDevNames
    kwargs

    Returns
    -------

    """
    buff_size = 1024
    while True:
        buff = PyDAQmx.create_string_buffer(buff_size)
        try:
            if not not len(args):
                fun(args[0], buff, buff_size)
            else:
                fun(buff, buff_size)
            break

        except Exception as e:
            if isinstance(e, PyDAQmx.DAQmxFunctions.DAQException):
                if e.error == -200228:  # BufferTooSmallForStringError
                    buff_size = 2 * buff_size
                else:
                    raise e
            else:
                raise e
    return buff.value.decode()


class DAQmx:

    def __init__(self):
        super().__init__()
        self.devices = []
        self.channels = []
        self._device = None
        self._task = None
        self.update_NIDAQ_devices()
        self.update_NIDAQ_channels()
        self.c_callback = None
        self.callback_data = None
        self.is_scalar = True
        self.write_buffer = np.array([0.])

    @property
    def task(self):
        return self._task

    @property
    def device(self):
        return self._device

    @device.setter
    def device(self, device):
        if device not in self.devices:
            raise IOError(f'your device: {device} is not known or connected')
        self._device = device

    def update_NIDAQ_devices(self):
        self.devices = self.get_NIDAQ_devices()

    @classmethod
    def get_NIDAQ_devices(cls):
        """Get list of NI connected devices

        Returns
        -------
        list
            list of devices as strings to be used in subsequent commands
        """
        try:
            string = try_string_buffer(PyDAQmx.DAQmxGetSysDevNames)
            devices = string.split(', ')
            if devices == ['']:
                devices = []
            return devices
        except:
            return []

    def update_NIDAQ_channels(self, source_type=None):
        self.channels = self.get_NIDAQ_channels(self.devices, source_type=source_type)

    @classmethod
    def get_NIDAQ_channels(cls, devices=None, source_type=None):
        """Get the list of available channels for all NiDAq connected devices

        Parameters
        ----------
        devices: list
                 list of strings, each one being a connected device
        source_type: str
                     One of the entries of DAQ_NIDAQ_source enum

        Returns
        -------
        List of str containing device and channel names

        """
        if devices is None:
            devices = cls.get_NIDAQ_devices()

        if source_type is None:
            source_type = DAQ_NIDAQ_source.names()
        if not isinstance(source_type, list):
            source_type = [source_type]
        channels_tot = []
        if not not devices:
            for device in devices:
                for source in source_type:
                    if source == DAQ_NIDAQ_source['Analog_Input'].name:  # analog input
                        string = try_string_buffer(PyDAQmx.DAQmxGetDevAIPhysicalChans, device)
                    elif source == DAQ_NIDAQ_source['Counter'].name:  # counter
                        string = try_string_buffer(PyDAQmx.DAQmxGetDevCIPhysicalChans, device)
                    elif source == DAQ_NIDAQ_source['Analog_Output'].name:  # analog output
                        string = try_string_buffer(PyDAQmx.DAQmxGetDevAOPhysicalChans, device)
                    elif source == DAQ_NIDAQ_source['Digital_Output'].name:  # digital output
                        string = try_string_buffer(PyDAQmx.DAQmxGetDevDOLines, device)
                    elif source == DAQ_NIDAQ_source['Digital_Input'].name:  # digital output
                        string = try_string_buffer(PyDAQmx.DAQmxGetDevDILines, device)
                    elif source == DAQ_NIDAQ_source['Terminals'].name:  # digital output
                        string = try_string_buffer(PyDAQmx.DAQmxGetDevTerminals, device)

                    channels = string.split(', ')
                    if channels != ['']:
                        channels_tot.extend(channels)

        return channels_tot

    @classmethod
    def getAOMaxRate(cls, device):
        data = PyDAQmx.c_double()
        PyDAQmx.DAQmxGetDevAOMaxRate(device, PyDAQmx.byref(data))
        return data.value

    @classmethod
    def getAIMaxRate(cls, device):
        data = PyDAQmx.c_double()
        PyDAQmx.DAQmxGetDevAIMaxSingleChanRate(device, PyDAQmx.byref(data))
        return data.value

    @classmethod
    def isAnalogTriggeringSupported(cls, device):
        data = PyDAQmx.c_uint32()
        PyDAQmx.DAQmxGetDevAnlgTrigSupported(device, PyDAQmx.byref(data))
        return bool(data.value)

    @classmethod
    def isDigitalTriggeringSupported(cls, device):
        data = PyDAQmx.c_uint32()
        PyDAQmx.DAQmxGetDevDigTrigSupported(device, PyDAQmx.byref(data))
        return bool(data.value)

    @classmethod
    def getTriggeringSources(cls, devices=None):
        sources = []
        if devices is None:
            devices = cls.get_NIDAQ_devices()

        for device in devices:
            if cls.isDigitalTriggeringSupported(device):
                string = try_string_buffer(PyDAQmx.DAQmxGetDevTerminals, device)
                channels = [chan for chan in string.split(', ') if 'PFI' in chan]
                if channels != ['']:
                    sources.extend(channels)
            if cls.isAnalogTriggeringSupported(device):
                channels = cls.get_NIDAQ_channels(devices=[device], source_type='Analog_Input')
                if channels != ['']:
                    sources.extend(channels)
        return sources


    def update_task(self, channels=[], clock_settings=ClockSettings(), trigger_settings=TriggerSettings()):
        """

        """

        try:
            if self._task is not None:
                if isinstance(self._task, PyDAQmx.Task):
                    self._task.ClearTask()

                self._task = None
                self.c_callback = None


            self._task = PyDAQmx.Task()


            ## create all channels one task for one type of channels
            for channel in channels:
                if channel.source == 'Analog_Input': #analog input
                    if channel.analog_type == "Voltage":
                        err_code = self._task.CreateAIVoltageChan(channel.name, "",
                                     DAQ_termination[channel.termination].value,
                                     channel.value_min,
                                     channel.value_max,
                                     PyDAQmx.DAQmx_Val_Volts, None)

                    elif channel.analog_type == "Current":
                        err_code = self._task.CreateAICurrentChan(channel.name, "",
                                                                  DAQ_termination[channel.termination].value,
                                                                  channel.value_min,
                                                                  channel.value_max,
                                                                  PyDAQmx.DAQmx_Val_Amps, PyDAQmx.DAQmx_Val_Internal,
                                                                  0., None)

                    elif channel.analog_type == "Thermocouple":
                        err_code = self._task.CreateAIThrmcplChan(channel.name, "",
                                                                  channel.value_min,
                                                                  channel.value_max,
                                                                  PyDAQmx.DAQmx_Val_DegC,
                                                                  DAQ_termination[channel.thermo_type].value,
                                                                  PyDAQmx.DAQmx_Val_BuiltIn, 0., "")

                elif channel.source == 'Counter': #counter
                    if channel.counter_type == "Edge Counter":
                        err_code = self._task.CreateCICountEdgesChan(channel.name, "",
                                                                     Edge[channel.edge].value, 0,
                                                                     PyDAQmx.DAQmx_Val_CountUp)
                    elif channel.counter_type == "Clock Output":
                        err_code = self._task.CreateCOPulseChanFreq(channel.name, "",
                                                                    # units, Hertz in our case
                                                                    PyDAQmx.DAQmx_Val_Hz,
                                                                    # idle state
                                                                    PyDAQmx.DAQmx_Val_Low,
                                                                    # initial delay
                                                                    0,
                                                                    # pulse frequency
                                                                    channel.clock_frequency,
                                                                    # duty cycle of pulses, 0.5 such that
                                                                    # high and low duration are both
                                                                    # equal to count_interval
                                                                    0.5)
                    elif channel.counter_type == "SemiPeriod Input":
                        err_code = self._task.CreateCISemiPeriodChan(channel.name, "", 0, # expected min
                                                                     channel.value_max, # expected max
                                                                     PyDAQmx.DAQmx_Val_Ticks, "")
                        
                    
                    if not not err_code:
                        status = self.DAQmxGetErrorString(err_code)
                        raise IOError(status)

                elif channel.source == 'Analog_Output':  # Analog_Output
                    if channel.analog_type == "Voltage":
                        err_code = self._task.CreateAOVoltageChan(channel.name, "",
                                     channel.value_min,
                                     channel.value_max,
                                     PyDAQmx.DAQmx_Val_Volts, None)

                    if channel.analog_type == "Current":
                        err_code = self._task.CreateAOCurrentChan(channel.name, "",
                                     channel.value_min,
                                     channel.value_max,
                                     PyDAQmx.DAQmx_Val_Amps, None)

                elif channel.source == 'Digital_Output': #Digital_Output
                    err_code = self._task.CreateDOChan(channel.name, "", PyDAQmx.DAQmx_Val_ChanPerLine)
                    if not not err_code:
                        status = self.DAQmxGetErrorString(err_code)
                        raise IOError(status)

                elif channel.source == 'Digital_Input': #Digital_Input
                    err_code = self._task.CreateDIChan(channel.name, "", PyDAQmx.DAQmx_Val_ChanPerLine)
                    if not not err_code:
                        status = self.DAQmxGetErrorString(err_code)
                        raise IOError(status)

            ## configure the timing
            if clock_settings.repetition:
                mode = PyDAQmx.DAQmx_Val_ContSamps
            else:
                mode = PyDAQmx.DAQmx_Val_FiniteSamps
            if clock_settings.Nsamples > 1 and err_code == 0:
                if isinstance(clock_settings, ClockSettings):
                    err_code =\
                        self._task.CfgSampClkTiming(clock_settings.source, clock_settings.frequency,
                                                    Edge[clock_settings.edge].value,
                                                    mode,
                                                    clock_settings.Nsamples)
                elif isinstance(clock_settings, ChangeDetectionSettings):
                    err_code =\
                        self._task.CfgChangeDetectionTiming(clock_settings.rising_channel,
                                                            clock_settings.falling_channel,
                                                            mode,
                                                            clock_settings.Nsamples)

                if not not err_code:
                    status = self.DAQmxGetErrorString(err_code)
                    raise IOError(status)

            # if channel.source == 'Analog_Input':  # analog input
            #     if isinstance(clock_settings, ClockSettings):
            #         err_code =\
            #             self._task.CfgSampClkTiming(clock_settings.source, clock_settings.frequency,
            #                                         Edge[clock_settings.edge].value,
            #                                         mode,
            #                                         clock_settings.Nsamples)
            #     elif isinstance(clock_settings, ChangeDetectionSettings):
            #         err_code =\
            #             self._task.CfgChangeDetectionTiming(clock_settings.source,
            #                                                 clock_settings.rising_channel,
            #                                                 clock_settings.falling_channel,
            #                                                 mode,
            #                                                 clock_settings.Nsamples)
            #
            #     if not not err_code:
            #         status = self.DAQmxGetErrorString(err_code)
            #         raise IOError(status)
            #
            # elif channel.source == 'Counter':  # counter
            #     pass
            #
            # elif channel.source == 'Analog_Output':  # Analog_Output
            #     if clock_settings.Nsamples > 1 and err_code == 0:
            #
            #         if isinstance(clock_settings, ClockSettings):
            #             err_code = self._task.CfgSampClkTiming(clock_settings.source,
            #                                                    clock_settings.frequency,
            #                                                    Edge[clock_settings.edge].value,
            #                                                    mode,
            #                                                    clock_settings.Nsamples)
            #         elif isinstance(clock_settings, ChangeDetectionSettings):
            #             err_code = \
            #                 self._task.CfgChangeDetectionTiming(clock_settings.source,
            #                                                     clock_settings.rising_channel,
            #                                                     clock_settings.falling_channel,
            #                                                     mode,
            #                                                     clock_settings.Nsamples)
            #
            #         if not not err_code:
            #             status = self.DAQmxGetErrorString(err_code)
            #             raise IOError(status)
            #
            # else:
            #     pass

            ##configure the triggering
            if not trigger_settings.enable:
                err = self._task.DisableStartTrig()
                if err != 0:
                    raise IOError(self.DAQmxGetErrorString(err))
            else:
                if 'PF' in trigger_settings.trig_source:
                    self._task.CfgDigEdgeStartTrig(trigger_settings.trig_source, Edge[trigger_settings.edge].value)
                elif 'ai' in trigger_settings.trig_source:
                    self._task.CfgAnlgEdgeStartTrig(trigger_settings.trig_source,
                                                    Edge[trigger_settings.edge].value,
                                                    PyDAQmx.c_double(trigger_settings.level))
                else:
                    raise IOError('Unsupported Trigger source')

        except Exception as e:
            print(e)



    def register_callback(self, callback, event='done', nsamples=1):

        if event == 'done':
            self.c_callback = PyDAQmx.DAQmxDoneEventCallbackPtr(callback)
            self._task.RegisterDoneEvent(0, self.c_callback, None)
        elif event == 'sample':
            self.c_callback = PyDAQmx.DAQmxSignalEventCallbackPtr(callback)
            self._task.RegisterSignalEvent(PyDAQmx.DAQmx_Val_SampleCompleteEvent, 0, self.c_callback, None)
        elif event == 'Nsamples':
            self.c_callback = PyDAQmx.DAQmxEveryNSamplesEventCallbackPtr(callback)
            self._task.RegisterEveryNSamplesEvent(PyDAQmx.DAQmx_Val_Acquired_Into_Buffer, nsamples,
                                                  0, self.c_callback, None)

    def get_last_write_index(self):
        if self.task is not None:
            index_buffer = PyDAQmx.c_uint64()
            ret = self._task.GetWriteCurrWritePos(PyDAQmx.byref(index_buffer))
            if not not ret:
                raise IOError(self.DAQmxGetErrorString(ret))
            else:
                return index_buffer.value
        else:
            return -1

    def get_last_write(self):
        if self.is_scalar:
            return self.write_buffer[-1]
        else:
            index = self.get_last_write_index()
            if index != -1:
                return self.write_buffer[index % len(self.write_buffer)]

            else:
                return 0.

    def writeAnalog(self, Nsamples, Nchannels, values, autostart=False):
        """
        Write Nsamples on N analog output channels
        Parameters
        ----------
        Nsamples: (int) numver of samples to write on each channel
        Nchannels: (int) number of AO channels defined in the task
        values: (ndarray) 2D array (or flattened array) of size Nsamples * Nchannels

        Returns
        -------

        """
        if np.prod(values.shape) != Nsamples * Nchannels:
            raise ValueError(f'The shape of analog outputs values is incorrect, should be {Nsamples} x {Nchannels}')

        if len(values.shape) != 1:
            values = values.reshape((Nchannels * Nsamples))
        self.write_buffer = values

        timeout = -1
        if values.size == 1:
            self._task.WriteAnalogScalarF64(autostart, timeout, values[0], None)
            self.is_scalar = True

        else:
            self.is_scalar = False
            read = PyDAQmx.int32()
            self._task.WriteAnalogF64(Nsamples, autostart, timeout, PyDAQmx.DAQmx_Val_GroupByChannel, values,
                                           PyDAQmx.byref(read), None)
            if read.value != Nsamples:
                raise IOError(f'Insufficient number of samples have been written:{read.value}/{Nsamples}')

    def readAnalog(self, Nchannels, clock_settings):
        read = PyDAQmx.int32()
        N = clock_settings.Nsamples
        data = np.zeros(N * Nchannels, dtype=np.float64)
        timeout = N * Nchannels * 1 / clock_settings.frequency * 2  # set to twice the time it should take to acquire the data

        self._task.ReadAnalogF64(N, timeout, PyDAQmx.DAQmx_Val_GroupByChannel, data, len(data),
                                 PyDAQmx.byref(read), None)
        if read.value == N:
            return data
        else:
            raise IOError(f'Insufficient number of samples have been read:{read.value}/{N}')

    def readCounter(self, Nchannels, counting_time=10.):

        data_counter = np.zeros(Nchannels, dtype='uint32')
        read = PyDAQmx.int32()
        self._task.ReadCounterU32Ex(PyDAQmx.DAQmx_Val_Auto, 2*counting_time, PyDAQmx.DAQmx_Val_GroupByChannel,
                                    data_counter,
                                    Nchannels, PyDAQmx.byref(read), None)
        self._task.StopTask()

        if read.value == Nchannels:
            return data_counter
        else:
            raise IOError(f'Insufficient number of samples have been read:{read}/{Nchannels}')

    def readDigital(self, Nchannels):
        read = PyDAQmx.int32()
        bytes_sample = PyDAQmx.int32()
        data = np.zeros(Nchannels, dtype='uint8')
        self._task.ReadDigitalLines(Nchannels, 0, PyDAQmx.DAQmx_Val_GroupByChannel,
                                    data, Nchannels, PyDAQmx.byref(read), PyDAQmx.byref(bytes_sample), None);

        if read.value == Nchannels:
            return data
        else:
            raise IOError(f'Insufficient number of samples have been read:{read}/{Nchannels}')

    def writeDigital(self, Nchannels, values, autostart=False):
        if np.prod(values.shape) != Nchannels:
            raise ValueError(f'The shape of digital outputs values is incorrect, should be {Nchannels}')
        values.astype(np.uint8)
        written = PyDAQmx.int32()
        self._task.WriteDigitalLines(Nchannels, autostart, 0, PyDAQmx.DAQmx_Val_GroupByChannel,
                                      values, PyDAQmx.byref(written), None)
        if written.value != Nchannels:
            raise IOError(f'Insufficient number of samples have been written:{written}/{Nchannels}')

    @classmethod
    def getAIVoltageRange(cls, device='Dev1'):
        buff_size = 100
        ranges = ctypes.pointer((buff_size*ctypes.c_double)())
        ret = PyDAQmx.DAQmxGetDevAIVoltageRngs(device, ranges[0], buff_size)
        if ret == 0:
            return [tuple(ranges.contents[2*ind:2*(ind+1)]) for ind in range(int(buff_size/2-2))
                    if np.abs(ranges.contents[2*ind]) > 1e-12]
        return [(-10., 10.)]

    @classmethod
    def getAOVoltageRange(cls, device='Dev1'):
        buff_size = 100
        ranges = ctypes.pointer((buff_size*ctypes.c_double)())
        ret = PyDAQmx.DAQmxGetDevAOVoltageRngs(device, ranges[0], buff_size)
        if ret == 0:
            return [tuple(ranges.contents[2*ind:2*(ind+1)]) for ind in range(int(buff_size/2-2))
                    if np.abs(ranges.contents[2*ind]) > 1e-12]
        return [(-10., 10.)]

    def stop(self):
        if self._task is not None:
            self._task.StopTask()

    def start(self):
        if self._task is not None:
            self._task.StartTask()

    def close(self):
        """
            close the current task.
        """
        if self._task is not None:
            self._task.StopTask()
            self._task.ClearTask()
            self._task = None

    @classmethod
    def DAQmxGetErrorString(cls, error_code):
        if error_code is None:
            return ''
        else:
            buffer = PyDAQmx.create_string_buffer(1024)
            PyDAQmx.DAQmxGetErrorString(error_code, buffer, len(buffer))
            return buffer.value.decode()

    def isTaskDone(self):
        done = PyDAQmx.bool32(False)
        self._task.GetTaskComplete(PyDAQmx.byref(done))
        return bool(done.value)

    def waitTaskDone(self, timeout=10.):
        ret = self._task.WaitUntilTaskDone(timeout)
        if ret != 0:
            logger.info(self.DAQmxGetErrorString(ret))

    def refresh_hardware(self):
        """
            Refresh the NIDAQ hardware from settings values.

            See Also
            --------
            update_NIDAQ_devices, update_NIDAQ_channels
        """
        devices = self.update_NIDAQ_devices()
        self.update_NIDAQ_channels(devices)

if __name__ == '__main__':
    print(DAQmx.get_NIDAQ_channels())
    pass
