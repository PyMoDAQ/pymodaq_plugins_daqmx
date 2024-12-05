from pymodaq.control_modules.viewer_utility_classes import main
from pymodaq.control_modules.viewer_utility_classes import comon_parameters as viewer_params
from pymodaq_plugins_daqmx.hardware.national_instruments.daqmxni import AIChannel, AIThermoChannel, DAQmx, nidaqmx,\
    DAQ_termination, DAQ_thermocouples
from pymodaq_plugins_daqmx.hardware.national_instruments.daq_NIDAQmx import DAQ_NIDAQmx_base
from pymodaq_plugins_daqmx.hardware.national_instruments.daq_NIDAQmx_Viewer import DAQ_NIDAQmx_Viewer
from pymodaq.utils.logger import set_logger, get_module_name
logger = set_logger(get_module_name(__file__))


class DAQ_0DViewer_NIDAQmx(DAQ_NIDAQmx_Viewer):
    """
    Plugin for a 0D data visualization & acquisition with various NI modules plugged in a NI cDAQ.
    """

    channels_ai: str
    clock_settings_ai: str
    dict_device_input: dict
    live: bool
    data_tot: list
    Naverage: int
    ind_average: int

    params = viewer_params + [
        {'title': 'Display type:', 'name': 'display', 'type': 'list', 'limits': ['0D', '1D']},
        {'title': 'Module ref. :', 'name': 'module', 'type': 'list', 'limits': DAQmx.get_NIDAQ_devices()[1],
         'value': DAQmx.get_NIDAQ_devices()[1][0]
         },
        ] + DAQ_NIDAQmx_base.params

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)

    def ini_attributes(self):
        super().ini_attributes()
        self.controller: DAQmx = None
        self.channels_ai = None
        self.clock_settings_ai = None
        self.dict_device_input = None
        self.live = False  # True during a continuous grab
        self.data_tot = None
        self.Naverage = 1
        self.ind_average = 0

    def close(self):
        self.live = False
        self.controller.stop()
        self.controller.close()
        pass


if __name__ == '__main__':
    """Main section used during development tests"""
    main_file = False
    if main_file:
        main(__file__)
    else:
        try:
            print("In main")
            import nidaqmx as ni
            from pymodaq_plugins_daqmx.hardware.national_instruments.daqmxni import CurrentUnits, TemperatureUnits,\
                VoltageUnits, CJCSource

            # EXPLORE DEVICES
            devices = ni.system.System.local().devices
            print("devices {}".format(devices))
            print("devices names {}".format(devices.device_names))
            print("devices types {}".format([dev.product_type for dev in devices]))
            cdaq = devices[0]
            mod1 = cdaq.chassis_module_devices[0]  # Equivalent devices[1]
            mod2 = devices[2]
            mod3 = devices[3]
            try:
                usb1 = devices[4]
            except Exception as e:
                pass
            print("cDAQ modules: {}".format(mod.compact_daq_chassis_device.product_type for mod in [mod1, mod2, mod3]))

            # TEST RESOURCES
            try:
                for device in devices:
                    device.self_test_device()
            except Exception as e:
                print("Resources test failed: {}" .format(e))

            # CREATE CHANNELS
            channels_th = [AIThermoChannel(name="cDAQ1Mod1/ai0",
                                           source='Analog_Input',
                                           analog_type='Thermocouple',
                                           value_min=-100,
                                           value_max=1000,
                                           thermo_type=DAQ_thermocouples.K),
                           ]
            channels_voltage = [AIChannel(name="cDAQ1Mod3/ai0",
                                          source='Analog_Input',
                                          analog_type='voltage',
                                          value_min=-80.0e-3,
                                          value_max=80.0e-3,
                                          termination=DAQ_termination.Auto,
                                          ),
                                AIChannel(name="cDAQ1Mod3/ai1",
                                          source='Analog_Input',
                                          analog_type='voltage',
                                          value_min=-80.0e-3,
                                          value_max=80.0e-3,
                                          termination=DAQ_termination.Auto,
                                          ),
                                ]
            # CREATE TASK
            task_9211 = nidaqmx.Task()
            task_9205 = nidaqmx.Task()

            def callback_9211(task_handle, every_n_samples_event_type, number_of_samples, callback_data):
                data9211 = task_9211.read(5)
                print(data9211)

            def callback_9205(task_handle, every_n_samples_event_type, number_of_samples, callback_data):
                data9205 = task_9205.read(5)
                print(data9205)

            for channel in channels_th:
                task_9211.ai_channels.add_ai_thrmcpl_chan(channel.name,
                                                          "",
                                                          channel.value_min,
                                                          channel.value_max,
                                                          TemperatureUnits.DEG_C,
                                                          channel.thermo_type,
                                                          CJCSource.BUILT_IN,
                                                          0.,
                                                          "")
            for channel in channels_voltage:
                task_9205.ai_channels.add_ai_voltage_chan(channel.name,
                                                          "",
                                                          channel.termination,
                                                          channel.value_min,
                                                          channel.value_max,
                                                          VoltageUnits.VOLTS,
                                                          "")
            task_9211.timing.cfg_samp_clk_timing(5.0, None, nidaqmx.constants.Edge.RISING,
                                                 nidaqmx.constants.AcquisitionType.CONTINUOUS, 5)
            task_9211.register_every_n_samples_acquired_into_buffer_event(10, callback_9211)

            task_9205.timing.cfg_samp_clk_timing(10, None, nidaqmx.constants.Edge.RISING,
                                                 nidaqmx.constants.AcquisitionType.CONTINUOUS, 10)
            task_9205.register_every_n_samples_acquired_into_buffer_event(2, callback_9205)

            task_9211.start()
            task_9205.start()

            print("Acquisition in progress... Press enter to stop")
            input()

            task_9211.close()
            task_9205.close()

        except Exception as e:
            print("Exception ({}): {}".format(type(e), str(e)))
