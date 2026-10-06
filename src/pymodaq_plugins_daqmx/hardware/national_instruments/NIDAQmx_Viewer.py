import traceback

from pymodaq_plugins_daqmx.hardware.national_instruments.daqmxni import niDevice, niSystem, ProductCategory
from pymodaq_plugins_daqmx.hardware.national_instruments.NIDAQmx_base import NIDAQmx, DAQ_NIDAQmx_base, \
    TerminalConfiguration, UsageTypeAI, ChannelType, RTDType
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters as viewer_params
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.logger import set_logger, get_module_name

from pymodaq_utils import config as utils_config
from pymodaq_plugins_daqmx import config as daqmx_config
from pathlib import WindowsPath

logger = set_logger(get_module_name(__file__))


def merge_dicts_recursive(original: dict, update: dict) -> dict:
    """
    Recursively merges two dictionaries.
    - Keys/values from `update` add or modify those in `original`.
    - Empty values (None, {}, [], etc.) in `update` are ignored.
    - Nested dictionaries are merged recursively.
    """
    merged = original.copy()  # Start with a copy of the original to avoid mutation
    for key, value in update.items():
        # Skip empty values (None, empty dict, empty list, etc.)
        if value is None or (isinstance(value, (dict, list, set)) and not value):
            continue

        # If the key exists in both dictionaries and both values are dictionaries,
        # recursively merge them
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_dicts_recursive(merged[key], value)
        else:
            # Otherwise, overwrite or add the value
            merged[key] = value
    return merged


class DAQ_NIDAQmx_Viewer(DAQ_Viewer_base, DAQ_NIDAQmx_base):
    """
        ==================== ========================
        **Attributes**         **Type**
        *data_grabed_signal*   instance of Signal
        *params*               dictionary list
        *task*
        ==================== ========================

        See Also
        --------
        refresh_hardware
    """
    config_channels: list
    controller: NIDAQmx
    config_devices: list
    config_modules: list
    live: bool
    Naverage: int
    param_devices = NIDAQmx.get_NIDAQ_devices().device_names
    params = viewer_params + [
        {'title': 'Devices :', 'name': 'devices', 'type': 'list', 'limits': param_devices,
         'value': param_devices[0]
         },
        ] + DAQ_NIDAQmx_base.params

    def __init__(self, parent=None, params_state=None, control_type="0D"):
        DAQ_Viewer_base.__init__(self, parent, params_state)  # defines settings attribute and various other methods
        DAQ_NIDAQmx_base.__init__(self)

        self.Naverage = None
        self.live = False
        self.control_type = control_type  # could be "0D", "1D"
        if self.control_type == "0D":
            self.settings.child('NIDAQ_type').setLimits([ChannelType.ANALOG_INPUT.name,
                                                         ChannelType.COUNTER_INPUT.name,
                                                         ChannelType.DIGITAL_INPUT.name])
        elif self.control_type == "1D":
            self.settings.child('NIDAQ_type').setLimits([ChannelType.ANALOG_INPUT.name])

        self.settings.child('ao_settings').hide()
        self.settings.child('ao_channels').hide()

    def ini_attributes(self):
        super().ini_attributes()
        self.config_channels = []
        self.config_devices = []
        self.config_modules = []
        self.live = False
        self.Naverage = 1

    def ini_detector(self, controller=None):
        """
            Initialisation procedure of the detector.

            See Also
            --------
            daq_utils.ThreadCommand
        """
        try:
            if self.is_master:
                self.controller = NIDAQmx()
            else:
                self.controller = controller
            self.controller.device = niDevice(self.settings["devices"])

            # actions to perform in order to set properly the settings tree options
            self.commit_settings(self.settings.child('NIDAQ_type'))

            info = "Plugin Initialized"
            initialized = True
            logger.info("Detector {} initialized".format(self.control_type))
            return info, initialized

        except Exception as e:
            logger.info(traceback.format_exc())
            self.emit_status(ThreadCommand('Update_Status', [str(e), 'log']))
            info = str(e)
            initialized = False
            return info, initialized

    def commit_settings(self, param):
        """
            Activate the parameters changes in the hardware.

            =============== ================================ ===========================
            **Parameters**   **Type**                        **Description**
            *param*         instance of pyqtgraph.parameter   the parameter to activate
            =============== ================================ ===========================

            See Also
            --------
            update_NIDAQ_channels, update_task, refresh_hardware
        """
        DAQ_NIDAQmx_base.commit_settings(self, param)

        if param.parent() is not None:
            if param.parent().name() == 'ai_channels':
                device = param.opts['title'].split('/')[0]
                self.settings.child('clock_settings', 'frequency').setOpts(max=self.controller.getAIMaxSingleRate(device))
                volt_ranges = self.controller.getAIVoltageRange(device)
                if volt_ranges:
                    param.child('voltage_settings', 'volt_min').setValue(volt_ranges[0])
                    param.child('voltage_settings', 'volt_max').setValue(volt_ranges[1])
                curr_ranges = self.controller.getAICurrentRange(device)
                if curr_ranges:
                    param.child('current_settings', 'curr_min').setValue(curr_ranges[0])
                    param.child('current_settings', 'curr_max').setValue(curr_ranges[1])
            elif param.name() == 'devices':
                self.controller.device = niDevice(self.settings["devices"])
            elif param.name() == 'load_config':
                self.controller.configuration_sequence(self, self.controller.device)
                self.settings.child('load_config').hide()
                config_ai_channels = [ch for ch in self.config_channels if ch.source == ChannelType.ANALOG_INPUT]
                for ch in config_ai_channels:  # Browse configuration analog channels
                    self.settings.child('ai_channels').addNew(ch.name)
                    ch_par = [a for a in self.settings.child('ai_channels').childs if a.opts['title'] == ch.name][0]
                    ch_par.child("voltage_settings").show(ch.analog_type == UsageTypeAI.VOLTAGE)
                    ch_par.child("current_settings").show(ch.analog_type == UsageTypeAI.CURRENT)
                    ch_par.child("thermoc_settings").show(ch.analog_type == UsageTypeAI.TEMPERATURE_THERMOCOUPLE)
                    ch_par.child("rtd_settings").show(ch.analog_type == UsageTypeAI.TEMPERATURE_RTD)
                    match ch.analog_type:
                        case UsageTypeAI.VOLTAGE:
                            self.settings.child("ai_channels", ch_par.opts['name'], "ai_type").setValue("VOLTAGE")
                            self.settings.child("ai_channels", ch_par.opts['name'], "voltage_settings",
                                                "volt_min").setValue(
                                ch.value_min)
                            self.settings.child("ai_channels", ch_par.opts['name'], "voltage_settings",
                                                "volt_max").setValue(
                                ch.value_max)
                            self.settings.child("ai_channels", ch_par.opts['name'], "termination").setValue(
                                ch.termination.name)
                        case UsageTypeAI.CURRENT:
                            self.settings.child("ai_channels", ch_par.opts['name'], "ai_type").setValue("CURRENT")
                            self.settings.child("ai_channels", ch_par.opts['name'], "current_settings",
                                                "curr_min").setValue(
                                ch.value_min)
                            self.settings.child("ai_channels", ch_par.opts['name'], "current_settings",
                                                "curr_max").setValue(
                                ch.value_max)
                            self.settings.child("ai_channels", ch_par.opts['name'], "termination").setValue(
                                ch.termination.name)
                        case UsageTypeAI.TEMPERATURE_THERMOCOUPLE:
                            self.settings.child("ai_channels", ch_par.opts['name'], "ai_type").setValue(
                                "TEMPERATURE_THERMOCOUPLE")
                            self.settings.child("ai_channels",
                                                ch_par.opts['name'],
                                                "thermoc_settings",
                                                "thermoc_type").setValue(ch.thermo_type.name)
                            self.settings.child("ai_channels",
                                                ch_par.opts['name'],
                                                "thermoc_settings",
                                                "T_min").setValue(ch.value_min)
                            self.settings.child("ai_channels",
                                                ch_par.opts['name'],
                                                "thermoc_settings",
                                                "T_max").setValue(ch.value_max)
                            self.settings.child("ai_channels", ch_par.opts['name'], "termination").setValue(
                                TerminalConfiguration.DEFAULT.name)
                        case UsageTypeAI.TEMPERATURE_RTD:
                            ch_par.child("rtd_settings", "c-vd_coeff.").show(ch.rtd_type == RTDType.CUSTOM)
                            self.settings.child("ai_channels", ch_par.opts['name'], "ai_type").setValue(
                                "TEMPERATURE_RTD")
                            self.settings.child("ai_channels",
                                                ch_par.opts['name'],
                                                "rtd_settings",
                                                "min_value_in").setValue(ch.value_min)
                            self.settings.child("ai_channels",
                                                ch_par.opts['name'],
                                                "rtd_settings",
                                                "max_value_in").setValue(ch.value_max)
                            self.settings.child("ai_channels",
                                                ch_par.opts['name'],
                                                "rtd_settings",
                                                "temp_unit").setValue(ch.units.name)
                            self.settings.child("ai_channels",
                                                ch_par.opts['name'],
                                                "rtd_settings",
                                                "resistance_config").setValue(ch.resistance_config.name)
                            self.settings.child("ai_channels",
                                                ch_par.opts['name'],
                                                "rtd_settings",
                                                "r0").setValue(ch.r_0)
                            self.settings.child("ai_channels",
                                                ch_par.opts['name'],
                                                "rtd_settings",
                                                "rtd_type").setValue(ch.rtd_type.name)
                            self.settings.child("ai_channels",
                                                ch_par.opts['name'],
                                                "rtd_settings", "c-vd_coeff.",
                                                "a_c-vd_coeff").setValue(ch.a_cvd_coeff)
                            self.settings.child("ai_channels",
                                                ch_par.opts['name'],
                                                "rtd_settings", "c-vd_coeff.",
                                                "b_c-vd_coeff").setValue(ch.b_cvd_coeff)
                            self.settings.child("ai_channels",
                                                ch_par.opts['name'],
                                                "rtd_settings", "c-vd_coeff.",
                                                "c_c-vd_coeff").setValue(ch.c_cvd_coeff)
                            self.settings.child("ai_channels",
                                                ch_par.opts['name'],
                                                "rtd_settings",
                                                "current_excit_src").setValue(ch.current_excit_source.name)
                            self.settings.child("ai_channels",
                                                ch_par.opts['name'],
                                                "rtd_settings",
                                                "i_ex_value").setValue(ch.current_excit_val)
                            self.settings.child("ai_channels", ch_par.opts['name'], "termination").setValue(
                                TerminalConfiguration.DEFAULT.name)
                self.channels = self.get_channels_from_settings()
                self.set_max_frequency()  # Set the acquisition frequency to the device maximum frequency

            elif param.name() == 'save_config' and param.value():
                logger.info("********** CONFIGURATION BACKING UP SEQUENCE INITIALIZED **********")
                try:
                    config_dict = {'title': 'Configuration file of the DAQmx plugin', 'NIDAQ_Devices': {}}
                    devices_collection = niSystem.local().devices

                    # CONFIGURATION OF THE "DEVICES"
                    for device in devices_collection:
                        if device.product_category == ProductCategory.COMPACT_DAQ_CHASSIS:
                            device_name = device.name
                            device_product = device.product_type
                            dev_dict_len = len(config_dict['NIDAQ_Devices'])
                            if dev_dict_len < 9:
                                toml_subsection_extension_name = "DEVICE0" + str(dev_dict_len + 1)
                            elif dev_dict_len < 99:
                                toml_subsection_extension_name = "DEVICE" + str(dev_dict_len + 1)
                            config_dict['NIDAQ_Devices'][toml_subsection_extension_name] = \
                                {'title': "Configuration entry for a NIDAQmx device", 'name': device_name,
                                 'product': device_product}

                    # CONFIGURATION OF THE MODULES
                    temporary_NIDAQ_devices_length = len(config_dict['NIDAQ_Devices']['DEVICE01']) # there is supposed at least one chassis to be plugged
                    modules_dict = {}
                    for device in devices_collection:
                        if device.product_category == ProductCategory.C_SERIES_MODULE:
                            cDAQ_chassis_name = device.compact_daq_chassis_device.name
                            for ni_daq_device in config_dict['NIDAQ_Devices']:
                                if config_dict['NIDAQ_Devices'][ni_daq_device]['name'] == cDAQ_chassis_name:
                                    module_number = len(config_dict['NIDAQ_Devices'][ni_daq_device]) - temporary_NIDAQ_devices_length
                                    toml_subsection_extension_name = "MODULE0" + str(module_number + 1) # there is supposed to be no more than 9 modules on a device
                                    config_dict['NIDAQ_Devices'][ni_daq_device][toml_subsection_extension_name] = \
                                        {'title': 'Example of module plugged in a NIDAQmx device',
                                         'name': device.name,
                                         'product': device.product_type}
                                    modules_dict[device.name] = {'chassis_id' : ni_daq_device, 'module_id': toml_subsection_extension_name} # <- à utiliser pour suites dev

                    # CONFIGURATION OF THE DAQmx CHANNELS
                    cfs_list = self.get_channels_from_settings(from_all_devices=True) # "cfs" for "channels from settings"
                    abbrev_chan_type_dict = {ChannelType.ANALOG_INPUT : 'ai',
                                             ChannelType.ANALOG_OUTPUT : 'ao',
                                             ChannelType.COUNTER_INPUT : 'ci',
                                             ChannelType.COUNTER_OUTPUT : 'co',
                                             ChannelType.DIGITAL_INPUT : 'di',
                                             ChannelType.DIGITAL_OUTPUT : 'do'}
                    for cfs in cfs_list:
                        config_string_to_write = ""
                        cfs_config_dict = {}
                        cfs_name = cfs.name
                        cfs_source = cfs.source.name
                        if cfs.source in [ChannelType.ANALOG_INPUT, ChannelType.ANALOG_OUTPUT]:
                            cfs_analog_type = cfs.analog_type.name
                            cfs_value_min = cfs.value_min
                            cfs_value_max = cfs.value_max
                            config_string_to_write += 'name = "' + str(cfs_name) + '"\n' + "" \
                                                        'source = "' + str(cfs_source) + '"\n' + "" \
                                                        'analog_type = "' + str(cfs_analog_type) + '"\n' + "" \
                                                        'value_min = ' + str(cfs_value_min) + '\n' + "" \
                                                        'value_max = ' + str(cfs_value_max) + '\n'
                            cfs_config_dict['name'] = cfs_name
                            cfs_config_dict['source'] = cfs_source
                            cfs_config_dict['analog_type'] = cfs_analog_type
                            cfs_config_dict['value_min'] = cfs_value_min
                            cfs_config_dict['value_max'] = cfs_value_max
                            if cfs.source == ChannelType.ANALOG_INPUT:
                                cfs_termination = cfs.termination.name
                                match cfs.analog_type:
                                    case UsageTypeAI.CURRENT:
                                        cfs_info = "Example of AI current channel"
                                        cfs_config_dict['termination'] = cfs_termination
                                    case UsageTypeAI.VOLTAGE:
                                        cfs_info = "Example of AI voltage channel"
                                        cfs_config_dict['termination'] = cfs_termination
                                    case UsageTypeAI.TEMPERATURE_THERMOCOUPLE:
                                        cfs_info = "Example of AI thermocouple channel"
                                        cfs_thermo_type = cfs.thermo_type.name
                                        cfs_config_dict['thermo_type'] = cfs_thermo_type
                                        config_string_to_write += 'thermo_type = "' + str(cfs_thermo_type) + '"\n'
                                    # The other AI type cases are still to implement
                            else:
                                pass # to complete (for analog outputs, and counter or digital channels)
                        cfs_config_dict['info'] = cfs_info
                        [module_name, physical_chan_name] = cfs_name.split('/')
                        chassis_id = modules_dict[module_name]['chassis_id']
                        module_id = modules_dict[module_name]['module_id']
                        abbrev_chan_type = abbrev_chan_type_dict[cfs.source]
                        if abbrev_chan_type not in config_dict['NIDAQ_Devices'][chassis_id][module_id]:
                            config_dict['NIDAQ_Devices'][chassis_id][module_id][abbrev_chan_type] = {}
                        chan_num_str = physical_chan_name.strip('ai')
                        if int(chan_num_str) < 10:
                          chan_id_num = "0" + chan_num_str
                        # if chan_type_dict_len < 9:
                        #   chan_id_num = "0" + str(chan_type_dict_len + 1)
                        else :
                            chan_id_num = chan_num_str # there is supposed to be no more than 99 channels on one module
                        chan_id = abbrev_chan_type+chan_id_num
                        config_dict['NIDAQ_Devices'][chassis_id][module_id][abbrev_chan_type][physical_chan_name] = cfs_config_dict

                    merged_config = merge_dicts_recursive(original=daqmx_config(), update=config_dict)
                    daqmx_config().update(merged_config)
                    daqmx_config.save()
                    config_file_path = daqmx_config.config_path
                    utils_config.create_toml_from_dict(daqmx_config(), config_file_path)
                    logger.info("********** CONFIGURATION BACKING UP SEQUENCE SUCCESSFULLY ENDED **********")
                except Exception as err:
                    logger.info("Configuration sequence error, verify if your config matches the hardware: {}".format(err))
                param.setValue(not param.value()) # button mechanical action : it turns back to its value before user click
            self.channels = self.get_channels_from_settings()
            self.get_max_frequency()  # Set the frequency 'max' option to the device maximum frequency and display it

    def get_max_frequency(self):
        """
            Get the maximum frequency according to the material's limits and display the information.
            This method is destined to be removed once set_max_frequency will work correctly.
        """
        # Destined to be removed when set_max_frequency will work correctly
        try:
            max_freq = int(self.controller.getAIMaxSingleRate(self.controller.device.name))
            self.settings.child('clock_settings', 'max_freq').setValue(max_freq)
        except:
            pass

    def set_max_frequency(self):
        """
            Set the maximum frequency applicable to the frequency parameter according to material's limits.
        """
        # Opts 'max' get the right value but doesn't update the viewer which keep as max the initial max value
        try:
            max_freq = int(self.controller.getAIMaxSingleRate(self.controller.device.name))
            self.settings.child('clock_settings', 'frequency').setOpts(max=max_freq)
            self.settings.child('clock_settings', 'frequency').emitStateChanged('max', max_freq)
            self.settings.child('clock_settings', 'frequency')._emitOptionsChanged(
                self.settings.child('clock_settings', 'frequency'), {'max': max_freq})
        except:
            pass

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        try:
            DAQ_NIDAQmx_base.stop(self)
            self.live = False
            logger.info("Acquisition stopped.")
        except Exception:
            pass
        self.emit_status(ThreadCommand('Update_Status', ['Acquisition stopped.']))
        return ''

    def close(self):
        self.live = False
        self.stop()
        self.controller.close()
