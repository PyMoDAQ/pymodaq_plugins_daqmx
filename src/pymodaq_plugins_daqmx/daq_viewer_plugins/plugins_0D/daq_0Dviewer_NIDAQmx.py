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
    main_file = True
    if main_file:
        main(__file__)
    else:
        try:
            print("In main")
            import nidaqmx

            logger.info("DAQ Sources names{}".format(DAQ_NIDAQ_source.names()))
            logger.info("DAQ Sources members{}".format(DAQ_NIDAQ_source.members()))
            logger.info("DAQ Sources names0{}".format(DAQ_NIDAQ_source.names()[0]))
            logger.info("DAQ Sources members0{}".format(DAQ_NIDAQ_source.members()[0]))
            channels = [AIThermoChannel(name="cDAQ1Mod1/ai0",
                                        source='Analog_Input',
                                        analog_type='Thermocouple',
                                        value_min=-80.0e-3,
                                        value_max=80.0e-3,
                                        termination='Diff',
                                        thermo_type=DAQ_thermocouples.K),
                       ]
            # Create Task
            print("DAQ_thermocouples.names ", DAQ_thermocouples.names())
            print("DAQ_thermocouples.K ", nidaqmx.constants.ThermocoupleType.K)
            print("DAQ_thermocouples.K type", type(nidaqmx.constants.ThermocoupleType.K))
            print("DAQ_thermocouples.K ", DAQ_thermocouples.K)
            print("DAQ_thermocouples.K type ", type(DAQ_thermocouples.K))
            print("channel.thermo_type ", channels[0].thermo_type)
            task = nidaqmx.Task()
            for channel in channels:
                task.ai_channels.add_ai_thrmcpl_chan(physical_channel=channel.name,
                                                     # name_to_assign_to_channel="Channel 01",
                                                     min_val=channel.value_min,
                                                     max_val=channel.value_max,
                                                     units=TemperatureUnits.DEG_C,
                                                     thermocouple_type=channel.thermo_type,
                                                     # cjc_source=CJCSource.BUILT_IN,
                                                     # cjc_val="",
                                                     # cjc_channel="",
                                                     )
            NIDAQ_Devices = nidaqmx.system.System.local().devices

            print("NIDAQ devices ", NIDAQ_Devices)
            print("NIDAQ devices names ", NIDAQ_Devices.device_names)

            Chassis = NIDAQ_Devices[0]
            Module01 = NIDAQ_Devices[1]
            Module02 = NIDAQ_Devices[2]
            print("Chassis={}, Module01={}, Module02={}" .format(Chassis, Module01, Module02))

            # Test resources
            try:
                Chassis.self_test_device()
                Module01.self_test_device()
                Module02.self_test_device()
            except Exception as e:
                print("Resources test failed: {}" .format(e))

            print("Chassis: name={}, Num={}".format(Chassis.name, Chassis.product_type))
            print("Module01: name={}, Num={}".format(Module01.name, Module01.product_type))
            print("Module02: name={}, Num={}".format(Module02.name, Module02.product_type))

            print("channel 01 name : ", channels[0].name)
            data = task.read()
            print("data = ", data)
            print("type(data) = ", type(data))
            print("type(data[0]) = ", type(data[0]))

            task.close()

        except Exception as e:
            print("Exception ({}): {}".format(type(e), str(e)))