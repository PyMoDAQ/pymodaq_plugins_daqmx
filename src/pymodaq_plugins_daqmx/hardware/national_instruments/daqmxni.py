import time
import traceback
from enum import IntEnum
import numpy as np
from pymodaq.utils.logger import set_logger, get_module_name

from nidaqmx.constants import AcquisitionType, VoltageUnits, CurrentUnits, CurrentShuntResistorLocation, \
                                TemperatureUnits, CJCSource, CountDirection, Level, FrequencyUnits, TimeUnits, \
                                LineGrouping
from pymodaq_plugins_daqmx.hardware.national_instruments import UsageTypeAI, Edge, TerminalConfiguration, ThermocoupleType

from nidaqmx.system import System as niSystem
from nidaqmx.system.device import Device as niDevice
from nidaqmx import Task as niTask
from nidaqmx.errors import DaqError, DAQmxErrors
from pymodaq_plugins_daqmx import config


logger = set_logger(get_module_name(__file__))


class IntEnumExtend(IntEnum):
    """
        This class expose 3 privates and undocumented methods of Enum
    """
    @classmethod
    def names(cls):
        return cls._member_names_
        # [item.name for item in cls.__members__.items()]
        # [name for name, member in cls.__members__.items()]

    @classmethod
    def members(cls):
        return list(cls._member_map_.values())
        # [member for name, member in cls.__members__.items()]
        # [item.member for item in cls.__members__.items()]

    @classmethod
    def values(cls):
        return [cls[name].value for name in cls._member_names_]
        # [cls[name].value for name, member in cls.__members__.items()]


class DAQ_NIDAQ_source(IntEnumExtend):
    """
        Enum class of NIDAQ_source

        =============== ==========
        **Attributes**   **Type**
        *Analog_Input*   int
        *Counter*        int
        =============== ==========
    """
    Analog_Input = 0
    Analog_Output = 1
    Counter = 2
    Digital_Input = 3
    Digital_Output = 4
    Terminals = 5

    @classmethod
    def sources0D(self):
        return [self.Analog_Input.name, DAQ_NIDAQ_source.Counter.name, DAQ_NIDAQ_source.Digital_Input.name]

    @classmethod
    def sources1D(self):
        return [self.Analog_Input.name]

    @classmethod
    def Actuator(self):
        return [self.Analog_Output.name]


class ClockSettingsBase:
    def __init__(self, Nsamples=1000, repetition=False):

        self.Nsamples = Nsamples
        self.repetition = repetition


class ClockSettings(ClockSettingsBase):
    def __init__(self, source=None, frequency=1000, Nsamples=1000, edge=Edge.RISING, repetition=False):
        super().__init__(Nsamples, repetition)
        self.source = source
        assert edge in Edge
        self.frequency = frequency
        self.edge = edge


class ChangeDetectionSettings(ClockSettingsBase):
    def __init__(self, Nsamples=1000, rising_channel='', falling_channel='',
                 repetition=False):
        super().__init__(Nsamples, repetition)
        self.rising_channel = rising_channel
        self.falling_channel = falling_channel


class TriggerSettings:
    def __init__(self, trig_source='', enable=False, edge=Edge.RISING, level=0.1):
        assert edge in Edge
        self.trig_source = trig_source
        self.enable = enable
        self.edge = edge
        self.level = level


class Channel:
    def __init__(self, name='', source=DAQ_NIDAQ_source.Analog_Input):
        """
        Parameters
        ----------

        """
        self.name = name
        assert source in DAQ_NIDAQ_source.names()
        self.source = source


class AChannel(Channel):
    def __init__(self, analog_type=UsageTypeAI.VOLTAGE, value_min=-10., value_max=+10., **kwargs):
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
    def __init__(self, termination=TerminalConfiguration.DEFAULT, **kwargs):
        super().__init__(**kwargs)
        assert termination in TerminalConfiguration
        self.termination = termination


class AIThermoChannel(AIChannel):
    def __init__(self, thermo_type=ThermocoupleType.K, **kwargs):
        super().__init__(**kwargs)
        assert thermo_type in ThermocoupleType
        self.thermo_type = thermo_type


class AOChannel(AChannel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Counter(Channel):
    def __init__(self, edge=Edge.RISING, **kwargs):
        assert edge in Edge
        super().__init__(**kwargs)
        self.edge = edge
        self.counter_type = "Edge Counter"


class ClockCounter(Counter):
    def __init__(self, clock_frequency=100, **kwargs):
        super().__init__(**kwargs)
        self.clock_frequency = clock_frequency
        self.counter_type = "Clock Output"


class DigitalChannel(Channel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class DOChannel(DigitalChannel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class DIChannel(DigitalChannel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class DAQmx:
    """Wrapper around the NIDAQmx package giving an easy-to-use object to instantiate channels and tasks"""
    def __init__(self):
        self.devices = []
        self.channels = []
        self._device = None
        self._task = None
        self.update_NIDAQ_devices()
        self.update_NIDAQ_channels()
        self.c_callback = None  # A qui servent ces callback ??
        self.callback_data = None
        self.is_scalar = True
        self.write_buffer = np.array([0.])  # ou est utilisé ce buffer??

    @property
    def task(self):
        return self._task

    @property
    def device(self):
        return self._device

    @device.setter
    def device(self, device):
        if device not in self.devices.device_names:
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
            devices = niSystem.local().devices
            if devices == ['']:
                devices = []
            return devices
        except DaqError as e:
            return e.error_code

    def update_NIDAQ_channels(self, source_type=None):
        self.channels = self.get_NIDAQ_channels(self.devices.device_names, source_type=source_type)

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
            devices = cls.get_NIDAQ_devices().device_names

        if source_type is None:
            source_type = DAQ_NIDAQ_source.names()
        if not isinstance(source_type, list):
            source_type = [source_type]
        channels_tot = []
        channels = []
        if not not devices:
            for device in devices:
                for source in source_type:
                    if source == DAQ_NIDAQ_source.Analog_Input.name:  # analog input
                        channels = niDevice(device).ai_physical_chans.channel_names
                    elif source == DAQ_NIDAQ_source.Analog_Output.name:  # analog output
                        channels = niDevice(device).ao_physical_chans.channel_names
                    elif source == DAQ_NIDAQ_source.Counter.name:  # counter
                        channels = niDevice(device).ci_physical_chans.channel_names
                    elif source == DAQ_NIDAQ_source.Digital_Output.name:  # digital output
                        channels = niDevice(device).do_lines.channel_names
                    elif source == DAQ_NIDAQ_source.Digital_Input.name:  # digital iutput
                        channels = niDevice(device).di_lines.channel_names
                    elif source == DAQ_NIDAQ_source.Terminals.name:  # terminals
                        channels = niDevice(device).terminals

                    if channels != ['']:
                        channels_tot.extend(channels)

        return channels_tot

    def configuration_sequence(self, viewer, current_device):
        """Configure each  / modules / channels as giver by the user in the configuration file

        Read the .toml file to get the desired hardware configuration,
        and send the nidaqmx a sequence which set up each channel.
        """
        logger.info("********** CONFIGURATION SEQUENCE INITIALIZED **********")
        devices_info = [dev.name + ': ' + dev.product_type for dev in self.devices]
        logger.info("Detected devices: {}".format(devices_info))
        try:
            viewer.config_devices = [config["NIDAQ_Devices", dev].get('name') for dev in viewer.config["NIDAQ_Devices"]
                                     if "Mod" not in config["NIDAQ_Devices", dev].get('name')]
            for dev in config["NIDAQ_Devices"]:
                if not isinstance(config["NIDAQ_Devices", dev], dict):
                    continue
                try:
                    device_name = config["NIDAQ_Devices", dev].get('name')
                    if not device_name == current_device.name:
                        continue
                    device_product = config["NIDAQ_Devices", dev].get('product')
                    device = niDevice(device_name)
                    assert device in self.devices and device.product_type == device_product, device.name
                except AssertionError as err:
                    logger.error("Device {} not detected: {}".format(device_name, err))
                    continue
                for mod in config["NIDAQ_Devices", dev]:
                    if not isinstance(config["NIDAQ_Devices", dev, mod], dict):
                        continue
                    try:
                        module_name = config["NIDAQ_Devices", dev, mod].get('name')
                        module_product = config["NIDAQ_Devices", dev, mod].get('product')
                        module = niDevice(module_name)
                        assert module in self.devices and module.product_type == module_product, module.name
                        viewer.config_modules.append(config["NIDAQ_Devices", dev, mod].get('name'))
                    except AssertionError as err:
                        logger.error("Module {} not detected: {}".format(module_name, err))
                        continue
                    for source in config["NIDAQ_Devices", dev, mod]:
                        if not isinstance(config["NIDAQ_Devices", dev, mod, source], dict):
                            continue
                        if source == "ai":
                            ai = config["NIDAQ_Devices", dev, mod, source]
                            for ch in ai.keys():
                                name = module_name + "/" + str(ch)
                                term = ai[ch].get("termination")
                                if ai[ch].get("analog_type") == UsageTypeAI.VOLTAGE.name:
                                    viewer.config_channels.append(AIChannel
                                                                  (name=name,
                                                                   source=ai[ch].get("source"),
                                                                   analog_type=ai[ch].get("analog_type"),
                                                                   value_min=float(ai[ch].get("value_min")),
                                                                   value_max=float(ai[ch].get("value_max")),
                                                                   termination=TerminalConfiguration.__getitem__(term),
                                                                   ))
                                elif ai[ch].get("analog_type") == UsageTypeAI.CURRENT.name:
                                    viewer.config_channels.append(AIChannel
                                                                (name=name,
                                                                 source=ai[ch].get("source"),
                                                                 analog_type=ai[ch].get("analog_type"),
                                                                 value_min=float(ai[ch].get("value_min")),
                                                                 value_max=float(ai[ch].get("value_max")),
                                                                 termination=TerminalConfiguration.__getitem__(term),
                                                                 ))
                                elif ai[ch].get("analog_type") == UsageTypeAI.TEMPERATURE_THERMOCOUPLE.name or \
                                        ai[ch].get("analog_type") == "Thermocouple":
                                    th = ai[ch].get("thermo_type")
                                    viewer.config_channels.append(AIThermoChannel
                                                                  (name=name,
                                                                   source=ai[ch].get("source"),
                                                                   analog_type=ai[ch].get("analog_type"),
                                                                   value_min=float(ai[ch].get("value_min")),
                                                                   value_max=float(ai[ch].get("value_max")),
                                                                   thermo_type=ThermocoupleType.__getitem__(th),
                                                                   ))
            logger.info("Devices from config: {}".format(viewer.config_devices))
            logger.info("Modules from config: {}".format(viewer.config_modules))
            logger.info("Channels from config: {}".format([ch.name for ch in viewer.config_channels]))
        except AssertionError as err:
            logger.error("Configuration entries <{}> does not match the hardware ".format(err))
        except Exception as err:
            logger.info("Configuration sequence error, verify if your config matches the hardware: {}".format(err))
            pass
        logger.info("       ********** CONFIGURATION SEQUENCE SUCCESSFULLY ENDED **********")

    @classmethod
    def getAOMaxRate(cls, device):
        return niDevice(device).ao_max_rate

    @classmethod
    def getAIMaxRate(cls, device):
        return niDevice(device).ai_max_single_chan_rate

    @classmethod
    def isAnalogTriggeringSupported(cls, device):
        return niDevice(device).anlg_trig_supported

    @classmethod
    def isDigitalTriggeringSupported(cls, device):
        return niDevice(device).dig_trig_supported

    @classmethod
    def getTriggeringSources(cls, devices=None):
        sources = []
        if devices is None:
            devices = cls.get_NIDAQ_devices().device_names

        for device in devices:
            if cls.isDigitalTriggeringSupported(device):
                string = niDevice(device).terminals
                channels = [chan for chan in string if 'PFI' in chan]
                if channels != ['']:
                    sources.extend(channels)
            if cls.isAnalogTriggeringSupported(device):
                channels = niDevice(device).ai_physical_chans.channel_names
                if channels != ['']:
                    sources.extend(channels)
        return sources

    def update_task(self, channels=[], clock_settings=ClockSettings(), trigger_settings=TriggerSettings()):

        try:
            if self._task is not None:
                if isinstance(self._task, niTask):
                    self._task.close()

                self._task = None
                self.c_callback = None

            self._task = niTask()
            logger.info("TASK: {}".format(self._task))
            err_code = None

            # create all channels one task for one type of channels
            for channel in channels:
                if channel.source == DAQ_NIDAQ_source.Analog_Input.name:  # analog input
                    try:
                        if channel.analog_type == UsageTypeAI.VOLTAGE.name:
                            self._task.ai_channels.add_ai_voltage_chan(channel.name,
                                                                       "",
                                                                       channel.termination,
                                                                       channel.value_min,
                                                                       channel.value_max,
                                                                       VoltageUnits.VOLTS,
                                                                       "")

                        elif channel.analog_type == UsageTypeAI.CURRENT.name:
                            self._task.ai_channels.add_ai_current_chan(channel.name,
                                                                       "",
                                                                       channel.termination,
                                                                       channel.value_min,
                                                                       channel.value_max,
                                                                       CurrentUnits.AMPS,
                                                                       CurrentShuntResistorLocation.INTERNAL,
                                                                       0.,
                                                                       "")

                        elif channel.analog_type == UsageTypeAI.TEMPERATURE_THERMOCOUPLE.name:
                            self._task.ai_channels.add_ai_thrmcpl_chan(channel.name,
                                                                       "",
                                                                       channel.value_min,
                                                                       channel.value_max,
                                                                       TemperatureUnits.DEG_C,
                                                                       channel.thermo_type,
                                                                       CJCSource.BUILT_IN,
                                                                       0.,
                                                                       "")
                    except DaqError as e:
                        err_code = e.error_code
                    if err_code:
                        status = self.DAQmxGetErrorString(err_code)
                        raise IOError(status)
                elif channel.source == 'Counter':  # counter
                    try:
                        if channel.counter_type == "Edge Counter":
                            self._task.ci_channels.add_ci_count_edges_chan(channel.name, "",
                                                                           channel.edge, 0,
                                                                           CountDirection.COUNT_UP)

                        elif channel.counter_type == "Clock Output":
                            self._task.co_channels.add_co_pulse_chan_freq(channel.name, "clock task",
                                                                          FrequencyUnits.HZ,
                                                                          Level.LOW,
                                                                          0,
                                                                          channel.clock_frequency,
                                                                          0.5)

                        elif channel.counter_type == "SemiPeriod Input":
                            self._task.ci_channels.add_ci_semi_period_chan(channel.name, "counter task",
                                                                           0,  # expected min
                                                                           channel.value_max,  # expected max
                                                                           TimeUnits.TICKS, "")

                    except DaqError as e:
                        err_code = e.error_code

                    if not not err_code:
                        status = self.DAQmxGetErrorString(err_code)
                        raise IOError(status)

                    if not not err_code:
                        status = self.DAQmxGetErrorString(err_code)
                        raise IOError(status)
                elif channel.source == DAQ_NIDAQ_source.Analog_Output.name:  # Analog_Output
                    try:
                        if channel.analog_type == UsageTypeAI.VOLTAGE.name:
                            self._task.ao_channels.add_ao_voltage_chan(channel.name, "",
                                                                       channel.value_min,
                                                                       channel.value_max,
                                                                       VoltageUnits.VOLTS, None)

                        elif channel.analog_type == UsageTypeAI.CURRENT.name:
                            self._task.ao_channels.add_ao_current_chan(channel.name, "",
                                                                       channel.value_min,
                                                                       channel.value_max,
                                                                       VoltageUnits.VOLTS, None)
                    except DaqError as e:
                        err_code = e.error_code
                    if not not err_code:
                        status = self.DAQmxGetErrorString(err_code)
                        raise IOError(status)
                elif channel.source == DAQ_NIDAQ_source.Digital_Output.name:
                    try:
                        self._task.do_channels.add_do_chan(channel.name, "",
                                                           LineGrouping.CHAN_PER_LINE)
                    except DaqError as e:
                        err_code = e.error_code
                    if not not err_code:
                        status = self.DAQmxGetErrorString(err_code)
                        raise IOError(status)
                elif channel.source == DAQ_NIDAQ_source.Digital_Input.name:  # Digital_Input
                    try:
                        self._task.di_channels.add_di_chan(channel.name, "",
                                                           LineGrouping.CHAN_PER_LINE)
                    except DaqError as e:
                        err_code = e.error_code
                    if not not err_code:
                        status = self.DAQmxGetErrorString(err_code)
                        raise IOError(status)

            # configure the timing
            if clock_settings.repetition:
                mode = AcquisitionType.CONTINUOUS
            else:
                mode = AcquisitionType.FINITE
            if clock_settings.Nsamples > 1 and isinstance(err_code, type(None)):
                try:
                    if isinstance(clock_settings, ClockSettings):
                        self._task.timing.cfg_samp_clk_timing(clock_settings.frequency,
                                                              clock_settings.source,
                                                              clock_settings.edge,
                                                              mode,
                                                              clock_settings.Nsamples)
                    elif isinstance(clock_settings, ChangeDetectionSettings):
                        self._task.timing.cfg_change_detection_timing(clock_settings.rising_channel,
                                                                      clock_settings.falling_channel,
                                                                      mode,
                                                                      clock_settings.Nsamples)
                except DaqError as e:
                    err_code = e.error_code
                if not not err_code:
                    status = self.DAQmxGetErrorString(err_code)
                    logger.error(traceback.format_exc())
                    raise IOError(status)

            for channel in channels:
                if not trigger_settings.enable:
                    if channel.source == 'Counter':
                        pass  # Maybe here adding the configuration fastCTr0 with Ctr1 etc...?
                    else:
                        pass
                        # err = self._task.triggers.start_trigger.disable_start_trig()
                        # if err != 0:
                        #     raise IOError(self.DAQmxGetErrorString(err))
                else:
                    if 'PF' in trigger_settings.trig_source:
                        self._task.triggers.start_trigger.disable_start_trig()
                    elif 'ai' in trigger_settings.trig_source:
                        self._task.triggers.start_trigger.cfg_anlg_edge_start_trig(
                            trigger_settings.trig_source,
                            Edge[trigger_settings.edge],
                            trigger_settings.level)
                    else:
                        raise IOError('Unsupported Trigger source')
            logger.info("Task's channels{}".format(self._task.ai_channels.channel_names))
        except Exception as e:
            logger.error("Exception caught: {}".format(e))
            logger.error(traceback.format_exc())

    def register_callback(self, callback, event='done', nsamples=1):

        if event == 'done':
            self._task.register_done_event(callback)
            # NOT SURE HERE
        elif event == 'sample':
            self._task.register_every_n_samples_acquired_into_buffer_event(1, callback)
        elif event == 'Nsamples':
            self._task.register_every_n_samples_acquired_into_buffer_event(nsamples, callback)

    def readCounter(self):
        #    return 25

        time.sleep(1)
        self.value = self._task.read()

        #    t = Timer(counting_time,self.read)
        #    self._task.start()
        #    t.start()
        #    time.sleep(2*counting_time)
        #    print(self.value)
        return self.value

    @classmethod
    def getAIVoltageRange(cls, device='Dev1'):
        ret = niSystem.local().devices[device].ai_voltage_rngs  # todo self.devices[device].ai_voltage_rngs
        return [tuple(ret[6:8])]

    @classmethod
    def getAOVoltageRange(cls, device='Dev1'):
        ret = niSystem.local().devices[device].ao_voltage_rngs  # todo self.devices[device].ao_voltage_rngs
        return [tuple(ret)]  # [(-10., 10.)] Why this format is needed??

    def stop(self):
        if self._task is not None:
            self._task.stop()

    def start(self):
        if self._task is not None:
            self._task.start()

    def close(self):
        """
            close the current task.
        """
        if self._task is not None:
            self._task.stop()
            self._task.close()
            self._task = None

    @classmethod
    def DAQmxGetErrorString(cls, error_code):
        if error_code is None:
            return ''
        else:
            return DAQmxErrors(error_code).name

    def isTaskDone(self):
        return self._task.is_task_done()

    def waitTaskDone(self, timeout=10.):
        ret = self._task.wait_until_done(timeout)
        if ret != 0:
            logger.info(self.DAQmxGetErrorString(ret))

    def refresh_hardware(self):
        """
            Refresh the NIDAQ hardware from settings values.

            See Also
            --------
            update_NIDAQ_devices, update_NIDAQ_channels
        """
        self.update_NIDAQ_devices()
        self.update_NIDAQ_channels()


if __name__ == '__main__':
    pass
