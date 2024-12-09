from qtpy import QtWidgets
from qtpy.QtCore import Signal
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.parameter import Parameter
from pymodaq.utils.parameter.pymodaq_ptypes import registerParameterType, GroupParameter
from .daqmxni import DAQmx, DAQ_analog_types, DAQ_thermocouples, DAQ_termination, Edge, DAQ_NIDAQ_source, \
    ClockSettings, AIChannel, Counter, AIThermoChannel, AOChannel, TriggerSettings, DOChannel, DIChannel
logger = set_logger(get_module_name(__file__))


class ScalableGroupAI(GroupParameter):
    """
        |

        ================ =============
        **Attributes**    **Type**
        *opts*            dictionnary
        ================ =============

        See Also
        --------
        hardware.DAQ_Move_Stage_type
    """

    params = [{'title': 'AI type:', 'name': 'ai_type', 'type': 'list', 'limits': DAQ_analog_types.names()},
              {'title': 'Voltages:', 'name': 'voltage_settings', 'type': 'group', 'children': [
                  {'title': 'Voltage Min:', 'name': 'volt_min', 'type': 'float', 'value': -10.},
                  {'title': 'Voltage Max:', 'name': 'volt_max', 'type': 'float', 'value': 10.},
              ]},
              {'title': 'Current:', 'name': 'current_settings', 'type': 'group', 'visible': False, 'children': [
                  {'title': 'Current Min:', 'name': 'curr_min', 'type': 'float', 'value': -1, 'suffix': 'A'},
                  {'title': 'Current Max:', 'name': 'curr_max', 'type': 'float', 'value': 1, 'suffix': 'A'},
              ]},
              {'title': 'Thermocouple:', 'name': 'thermoc_settings', 'type': 'group', 'visible': False, 'children': [
                  {'title': 'Thc. type:', 'name': 'thermoc_type', 'type': 'list', 'limits': DAQ_thermocouples.names(),
                   'value': 'K'},
                  {'title': 'Temp. Min (°C):', 'name': 'T_min', 'type': 'float', 'value': 0, 'suffix': '°C'},
                  {'title': 'Temp. Max (°C):', 'name': 'T_max', 'type': 'float', 'value': 50, 'suffix': '°C'},
              ]},
              {'title': 'Termination:', 'name': 'termination', 'type': 'list', 'limits': DAQ_termination.names()},
              ]

    def __init__(self, **opts):
        opts['type'] = 'groupai'
        opts['addText'] = "Add"
        opts['addList'] = opts['limits']
        GroupParameter.__init__(self, **opts)

    def addNew(self, typ=None):
        """
            Add a child.

            =============== ===========
            **Parameters**   **Type**
            *typ*            string
            =============== ===========
        """
        childnames = [par.name() for par in self.children()]
        if childnames == []:
            newindex = 0
        else:
            newindex = len(childnames)

        child = {'title': typ, 'name': 'ai{:02.0f}'.format(newindex), 'type': 'group', 'children': self.params,
                 'removable': True, 'renamable': False}

        self.addChild(child)


registerParameterType('groupai', ScalableGroupAI, override=True)


class ScalableGroupAO(GroupParameter):
    """
        |

        ================ =============
        **Attributes**    **Type**
        *opts*            dictionnary
        ================ =============

        See Also
        --------
        hardware.DAQ_Move_Stage_type
    """

    params = [{'title': 'AO type:', 'name': 'ao_type', 'type': 'list', 'limits': DAQ_analog_types.names()[0:2]},
              {'title': 'Voltages:', 'name': 'voltage_settings', 'type': 'group', 'children': [
                  {'title': 'Voltage Min:', 'name': 'volt_min', 'type': 'list', 'value': -10., },
                  {'title': 'Voltage Max:', 'name': 'volt_max', 'type': 'list', 'value': 10., },
              ]},
              {'title': 'Current:', 'name': 'current_settings', 'type': 'group', 'visible': False, 'children': [
                  {'title': 'Current Min:', 'name': 'curr_min', 'type': 'float', 'value': -1, 'suffix': 'A'},
                  {'title': 'Current Max:', 'name': 'curr_max', 'type': 'float', 'value': 1, 'suffix': 'A'},
              ]},
              ]

    def __init__(self, **opts):
        opts['type'] = 'groupao'
        opts['addText'] = "Add"
        opts['addList'] = opts['limits']
        GroupParameter.__init__(self, **opts)

    def addNew(self, typ=None):
        """
            Add a child.

            =============== ===========
            **Parameters**   **Type**
            *typ*            string
            =============== ===========
        """
        childnames = [par.name() for par in self.children()]
        if childnames == []:
            newindex = 0
        else:
            newindex = len(childnames)

        child = {'title': typ, 'name': 'ao{:02.0f}'.format(newindex), 'type': 'group', 'children': self.params,
                 'removable': True, 'renamable': False}

        self.addChild(child)


registerParameterType('groupao', ScalableGroupAO, override=True)


class ScalableGroupCounter(GroupParameter):
    """
        |

        ================ =============
        **Attributes**    **Type**
        *opts*            dictionnary
        ================ =============

        See Also
        --------
        hardware.DAQ_Move_Stage_type
    """

    params = [{'title': 'Edge type:', 'name': 'edge', 'type': 'list', 'limits': Edge.names()}, ]

    def __init__(self, **opts):
        opts['type'] = 'groupcounter'
        opts['addText'] = "Add"
        opts['addList'] = opts['limits']
        GroupParameter.__init__(self, **opts)

    def addNew(self, typ=None):
        """
            Add a child.

            =============== ===========
            **Parameters**   **Type**
            *typ*            string
            =============== ===========
        """
        childnames = [par.name() for par in self.children()]
        if childnames == []:
            newindex = 0
        else:
            newindex = len(childnames)

        child = {'title': typ, 'name': 'counter{:02.0f}'.format(newindex), 'type': 'group', 'children': self.params,
                 'removable': True, 'renamable': False}

        self.addChild(child)


registerParameterType('groupcounter', ScalableGroupCounter, override=True)


class ScalableGroupDI(GroupParameter):
    """
    """

    params = []

    def __init__(self, **opts):
        opts['type'] = 'groupdi'
        opts['addText'] = "Add"
        opts['addList'] = opts['limits']
        GroupParameter.__init__(self, **opts)

    def addNew(self, typ=None):
        """
            Add a child.

            =============== ===========
            **Parameters**   **Type**
            *typ*            string
            =============== ===========
        """
        childnames = [par.name() for par in self.children()]
        if childnames == []:
            newindex = 0
        else:
            newindex = len(childnames)

        child = {'title': typ, 'name': 'di{:02.0f}'.format(newindex), 'type': 'group', 'children': self.params,
                 'removable': True, 'renamable': False}
        self.addChild(child)


registerParameterType('groupdi', ScalableGroupDI, override=True)


class ScalableGroupDO(GroupParameter):
    """
    """

    params = []

    def __init__(self, **opts):
        opts['type'] = 'groupdo'
        opts['addText'] = "Add"
        opts['addList'] = opts['limits']
        GroupParameter.__init__(self, **opts)

    def addNew(self, typ=None):
        """
            Add a child.

            =============== ===========
            **Parameters**   **Type**
            *typ*            string
            =============== ===========
        """
        childnames = [par.name() for par in self.children()]
        if childnames == []:
            newindex = 0
        else:
            newindex = len(childnames)

        child = {'title': typ, 'name': 'counter{:02.0f}'.format(newindex), 'type': 'group', 'children': self.params,
                 'removable': True, 'renamable': False}
        self.addChild(child)


registerParameterType('groupdo', ScalableGroupDO, override=True)


class DAQ_NIDAQmx_base:
    """
        Base NIDAQmx class for using DAQmx objects from daqmxni.py in the DAQ_NIDAQmx_Move & DAQ_NIDAQmx_Viewer
    """
    data_grabed_signal = Signal(list)
    param_instance = DAQmx()
    params = [{'title': 'Refresh hardware:', 'name': 'refresh_hardware', 'type': 'bool', 'value': False},
              {'title': 'Signal type:', 'name': 'NIDAQ_type', 'type': 'list', 'limits': DAQ_NIDAQ_source.names()},
              {'title': 'NSamples To Read', 'name': 'nsamplestoread', 'type': 'int', 'value': 1000, 'default': 1000,
               'min': 1},
              {'title': 'AO Settings:', 'name': 'ao_settings', 'type': 'group', 'children': [
                  {'title': 'Waveform:', 'name': 'waveform', 'type': 'list', 'value': 'DC',
                   'limits': ['DC', 'Sinus', 'Ramp']},
                  {'title': 'Controlled param:', 'name': 'cont_param', 'type': 'list', 'value': 'offset',
                   'limits': ['offset', 'amplitude', 'frequency']},
                  {'title': 'Waveform Settings:', 'name': 'waveform_settings', 'type': 'group', 'visible': False,
                   'children': [
                       {'title': 'Offset:', 'name': 'offset', 'type': 'float', 'value': 0., },
                       {'title': 'Amplitude:', 'name': 'amplitude', 'type': 'float', 'value': 1., },
                       {'title': 'Frequency:', 'name': 'frequency', 'type': 'float', 'value': 10., },
                   ]},
              ]},
              {'title': 'Clock Settings:', 'name': 'clock_settings', 'type': 'group', 'children': [
                  {'title': 'Nsamples:', 'name': 'Nsamples', 'type': 'int', 'value': 1000, 'default': 1000, 'min': 1},
                  {'title': 'Frequency:', 'name': 'frequency', 'type': 'float', 'value': 1000., 'default': 1000.,
                   'min': 0., 'suffix': 'Hz'},
                  {'title': 'Repetition?:', 'name': 'repetition', 'type': 'bool', 'value': False, },
              ]
               },
              {'title': 'AI Channels:', 'name': 'ai_channels', 'type': 'groupai',
               'limits': DAQmx.get_NIDAQ_channels(source_type='Analog_Input')},
              {'title': 'AO Channels:', 'name': 'ao_channels', 'type': 'groupao',
               'limits': DAQmx.get_NIDAQ_channels(source_type='Analog_Output')},
              {'title': 'DO Channels:', 'name': 'do_channels', 'type': 'groupdo',
               'limits': DAQmx.get_NIDAQ_channels(source_type='Digital_Output')},
              {'title': 'DI Channels:', 'name': 'di_channels', 'type': 'groupdi',
               'limits': DAQmx.get_NIDAQ_channels(source_type='Digital_Input')},
              {'title': 'Counter Settings:', 'name': 'counter_settings', 'type': 'group', 'visible': True, 'children': [
                  {'title': 'Counting time (ms):', 'name': 'counting_time', 'type': 'float', 'value': 100.,
                   'default': 100., 'min': 0.},
                  {'title': 'Counting Channels:', 'name': 'counter_channels', 'type': 'groupcounter',
                   'limits': DAQmx.get_NIDAQ_channels(source_type='Counter')},
              ]},
              {'title': 'Trigger Settings:', 'name': 'trigger_settings', 'type': 'group', 'visible': True, 'children': [
                  {'title': 'Enable?:', 'name': 'enable', 'type': 'bool', 'value': False, },
                  {'title': 'Trigger Source:', 'name': 'trigger_channel', 'type': 'list',
                   'limits': DAQmx.getTriggeringSources()},
                  {'title': 'Edge type:', 'name': 'edge', 'type': 'list', 'limits': Edge.names(), 'visible': False},
                  {'title': 'Level:', 'name': 'level', 'type': 'float', 'value': 1., 'visible': False}
              ]}
              ]

    def __init__(self):
        super().__init__()

        self.timer = None
        self.channels = None
        self.clock_settings = None
        self.trigger_settings = None
        self.live = False

    def commit_settings(self, param: Parameter):
        """
            Activate the parameters changes in the hardware.

            =============== ================================ ===========================
            **Parameters**   **Type**                        **Description**
            *param*         instance of pyqtgraph.parameter   the parameter to activate
            =============== ================================ ===========================

            See Also
            --------
            update_NIDAQ_channels, update_task, DAQ_NIDAQ_source, refresh_hardware
        """
        if param.name() == 'NIDAQ_devices':
            self.controller.update_NIDAQ_channels()
            self.update_task()

        if param.name() == 'NIDAQ_type':
            self.controller.update_NIDAQ_channels(param.value())
            if param.value() == DAQ_NIDAQ_source(0).name:  # analog input
                self.settings.child('clock_settings').show()
                self.settings.child('ai_channels').show()
                self.settings.child('ao_channels').hide()
                self.settings.child('ao_settings').hide()
                self.settings.child('counter_settings').hide()
                self.settings.child('do_channels').hide()
                self.settings.child('di_channels').hide()

            elif param.value() == DAQ_NIDAQ_source(1).name:  # analog output
                self.settings.child('clock_settings').show()
                self.settings.child('ai_channels').hide()
                self.settings.child('ao_channels').show()
                self.settings.child('ao_settings').show()
                self.settings.child('counter_settings').hide()
                self.settings.child('do_channels').hide()
                self.settings.child('di_channels').hide()

            elif param.value() == DAQ_NIDAQ_source(2).name:  # counter input
                self.settings.child('clock_settings').hide()
                self.settings.child('ai_channels').hide()
                self.settings.child('ao_channels').hide()
                self.settings.child('ao_settings').hide()
                self.settings.child('counter_settings').show()
                self.settings.child('do_channels').hide()
                self.settings.child('di_channels').hide()

            elif param.value() == DAQ_NIDAQ_source(3).name:  # Digital_Input
                self.settings.child('clock_settings').show()
                self.settings.child('ai_channels').hide()
                self.settings.child('ao_channels').show()
                self.settings.child('ao_settings').show()
                self.settings.child('counter_settings').hide()
                self.settings.child('do_channels').hide()
                self.settings.child('di_channels').show()

            elif param.value() == DAQ_NIDAQ_source(4).name:  # digital output
                self.settings.child('clock_settings').show()
                self.settings.child('ai_channels').hide()
                self.settings.child('ao_channels').hide()
                self.settings.child('ao_settings').hide()
                self.settings.child('counter_settings').hide()
                self.settings.child('do_channels').show()
                self.settings.child('di_channels').hide()
            self.update_task()

        elif param.name() == 'refresh_hardware':
            if param.value():
                self.controller.refresh_hardware()
                QtWidgets.QApplication.processEvents()
                self.settings.child('refresh_hardware').setValue(False)

        elif param.name() == 'ai_type':
            param.parent().child('voltage_settings').show(param.value() == 'Voltage')
            param.parent().child('current_settings').show(param.value() == 'Current')
            param.parent().child('thermoc_settings').show(param.value() == 'Thermocouple')
            self.update_task()

        elif param.name() == 'ao_type':
            param.parent().child('voltage_settings').show(param.value() == 'Voltage')
            param.parent().child('current_settings').show(param.value() == 'Current')
            self.update_task()

        elif param.name() == 'trigger_channel':
            param.parent().child('level').show('PF' not in param.opts['title'])

        else:
            self.update_task()

    def update_task(self):
        self.channels = self.get_channels_from_settings()
        logger.info("update_task - channels: {}".format(self.channels))
        self.clock_settings = ClockSettings(frequency=self.settings['clock_settings', 'frequency'],
                                            Nsamples=self.settings['clock_settings', 'Nsamples'],
                                            edge=Edge.Rising,
                                            repetition=self.live, )
        self.trigger_settings = \
            TriggerSettings(trig_source=self.settings['trigger_settings', 'trigger_channel'],
                            enable=self.settings['trigger_settings', 'enable'],
                            edge=Edge[self.settings['trigger_settings', 'edge']],
                            level=self.settings['trigger_settings', 'level'], )
        if not not self.channels:
            self.controller.update_task(self.channels, self.clock_settings, trigger_settings=self.trigger_settings)

    def get_channels_from_settings(self):
        channels = []
        if self.settings['NIDAQ_type'] == DAQ_NIDAQ_source(0).name:  # analog input
            for channel in self.settings.child('ai_channels').children():
                logger.info("get_channels_from_settings - channel {}".format(channel))
                analog_type = channel['ai_type']
                if analog_type == 'Voltage':
                    channels.append(AIChannel(name=channel.opts['title'],
                                              source='Analog_Input', analog_type=analog_type,
                                              value_min=channel['voltage_settings', 'volt_min'],
                                              value_max=channel['voltage_settings', 'volt_max'],
                                              termination=DAQ_termination[channel['termination']], ))
                elif analog_type == 'Current':
                    channels.append(AIChannel(name=channel.opts['title'],
                                              source='Analog_Input', analog_type=analog_type,
                                              value_min=channel['current_settings', 'curr_min'],
                                              value_max=channel['current_settings', 'curr_max'],
                                              termination=DAQ_termination[channel['termination']], ))
                elif analog_type == 'Thermocouple':
                    channels.append(AIThermoChannel(name=channel.opts['title'],
                                                    source='Analog_Input', analog_type=analog_type,
                                                    value_min=channel['thermoc_settings', 'T_min'],
                                                    value_max=channel['thermoc_settings', 'T_max'],
                                                    termination=channel['termination'],
                                                    thermo_type=DAQ_thermocouples[
                                                        channel['thermoc_settings', 'thermoc_type']], ))

        elif self.settings['NIDAQ_type'] == DAQ_NIDAQ_source(1).name:  # analog output
            for channel in self.settings.child('ao_channels').children():
                analog_type = channel['ao_type']
                channels.append(AOChannel(name=channel.opts['title'],
                                          source='Analog_Output', analog_type=analog_type,
                                          value_min=channel['voltage_settings', 'volt_min'],
                                          value_max=channel['voltage_settings', 'volt_max'],
                                          ))

        elif self.settings['NIDAQ_type'] == DAQ_NIDAQ_source(2).name:  # counter input
            for channel in self.settings.child('counter_settings', 'counter_channels').children():
                channels.append(Counter(name=channel.opts['title'],
                                        source='Counter', edge=channel['edge']))

        elif self.settings['NIDAQ_type'] == DAQ_NIDAQ_source(3).name:  # digital input
            for channel in self.settings.child('di_channels').children():
                channels.append(DIChannel(name=channel.opts['title'],
                                          source='Digital_Input'))

        elif self.settings['NIDAQ_type'] == DAQ_NIDAQ_source(4).name:  # Digital output
            for channel in self.settings.child('do_channels').children():
                channels.append(DOChannel(name=channel.opts['title'],
                                          source='Digital_Output'))
        channels = [ch for ch in channels if self.settings.child("dev_to_use").value() in ch.name]
        return channels

    def stop(self):
        """
        """
        if not not self.timer:
            self.timer.stop()
        QtWidgets.QApplication.processEvents()
        self.controller.stop()
