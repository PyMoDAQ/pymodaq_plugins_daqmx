from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Signal, QThread
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from pymodaq.utils.data import DataFromPlugins, Axis, DataActuator, DataToExport
import numpy as np
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
from easydict import EasyDict as edict

from pymodaq.control_modules.viewer_utility_classes import comon_parameters as viewer_params
from pymodaq.control_modules.move_utility_classes import comon_parameters_fun as actuator_params

from pymodaq.utils.parameter import Parameter
from pymodaq.utils.parameter.pymodaq_ptypes import registerParameterType, GroupParameter

from .daqmx import DAQmx, DAQ_analog_types, DAQ_thermocouples, DAQ_termination, Edge, DAQ_NIDAQ_source, \
    ClockSettings, AIChannel, Counter, AIThermoChannel, AOChannel, TriggerSettings, DOChannel, DIChannel


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
                  {'title': 'Voltage Min:', 'name': 'volt_min', 'type': 'list', 'value': -10.},
                  {'title': 'Voltage Max:', 'name': 'volt_max', 'type': 'list', 'value': 10.},
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

    def addNew(self, typ):
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

    def addNew(self, typ):
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

    def addNew(self, typ):
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

    def addNew(self, typ):
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

    def addNew(self, typ):
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


class DAQ_NIDAQmx_base(DAQmx):
    data_grabed_signal = Signal(list)

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

            elif param.value() == DAQ_NIDAQ_source(1).name:  # counter input
                self.settings.child('clock_settings').hide()
                self.settings.child('ai_channels').hide()
                self.settings.child('ao_channels').hide()
                self.settings.child('ao_settings').hide()
                self.settings.child('counter_settings').show()
                self.settings.child('do_channels').hide()
                self.settings.child('di_channels').hide()

            elif param.value() == DAQ_NIDAQ_source(2).name:  # analog output
                self.settings.child('clock_settings').show()
                self.settings.child('ai_channels').hide()
                self.settings.child('ao_channels').show()
                self.settings.child('ao_settings').show()
                self.settings.child('counter_settings').hide()
                self.settings.child('do_channels').hide()
                self.settings.child('di_channels').hide()

            elif param.value() == DAQ_NIDAQ_source(3).name:  # digital output
                self.settings.child('clock_settings').show()
                self.settings.child('ai_channels').hide()
                self.settings.child('ao_channels').hide()
                self.settings.child('ao_settings').hide()
                self.settings.child('counter_settings').hide()
                self.settings.child('do_channels').show()
                self.settings.child('di_channels').hide()

            elif param.value() == DAQ_NIDAQ_source(4).name:  # Digital_Input
                self.settings.child('clock_settings').show()
                self.settings.child('ai_channels').hide()
                self.settings.child('ao_channels').show()
                self.settings.child('ao_settings').show()
                self.settings.child('counter_settings').hide()
                self.settings.child('do_channels').hide()
                self.settings.child('di_channels').show()
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
            logger.info("not not self channel")
            self.controller.update_task(self.channels, self.clock_settings, trigger_settings=self.trigger_settings)

    def get_channels_from_settings(self):
        channels = []
        if self.settings['NIDAQ_type'] == DAQ_NIDAQ_source(0).name:  # analog input
            for channel in self.settings.child('ai_channels').children():
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

        elif self.settings['NIDAQ_type'] == DAQ_NIDAQ_source(1).name:  # counter input
            for channel in self.settings.child('counter_settings', 'counter_channels').children():
                channels.append(Counter(name=channel.opts['title'],
                                        source='Counter', edge=channel['edge']))

        elif self.settings['NIDAQ_type'] == DAQ_NIDAQ_source(2).name:  # analog output
            for channel in self.settings.child('ao_channels').children():
                analog_type = channel['ao_type']
                channels.append(AOChannel(name=channel.opts['title'],
                                          source='Analog_Output', analog_type=analog_type,
                                          value_min=channel['voltage_settings', 'volt_min'],
                                          value_max=channel['voltage_settings', 'volt_max'],
                                          ))
        elif self.settings['NIDAQ_type'] == DAQ_NIDAQ_source(3).name:  # Digital output
            for channel in self.settings.child('do_channels').children():
                channels.append(DOChannel(name=channel.opts['title'],
                                          source='Digital_Output'))
        elif self.settings['NIDAQ_type'] == DAQ_NIDAQ_source(4).name:  # digital input
            for channel in self.settings.child('di_channels').children():
                channels.append(DIChannel(name=channel.opts['title'],
                                          source='Digital_Input'))
        return channels

    def stop(self):
        """
        """
        if not not self.timer:
            self.timer.stop()
        QtWidgets.QApplication.processEvents()
        self.controller.stop()

class DAQ_NIDAQmx_Viewer(DAQ_Viewer_base, DAQ_NIDAQmx_base):
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

    live_mode_available = True
    params = viewer_params + DAQ_NIDAQmx_base.params

    def __init__(self, parent=None, params_state=None, control_type="0D"):
        DAQ_Viewer_base.__init__(self, parent, params_state)  # defines settings attribute and various other methods
        DAQ_NIDAQmx_base.__init__(self)

        self.Naverage = None
        self.live = False
        self.control_type = control_type  # could be "0D", "1D" or "Actuator"
        if self.control_type == "0D":
            self.settings.child('NIDAQ_type').setLimits(
                ['Analog_Input', 'Counter', 'Digital_Input'])  # analog input and counter
        elif self.control_type == "1D":
            self.settings.child('NIDAQ_type').setLimits(['Analog_Input'])
        elif self.control_type == "Actuator":
            self.settings.child('NIDAQ_type').setLimits(['Analog_Output'])

        self.settings.child('ao_settings').hide()
        self.settings.child('ao_channels').hide()

        # timer used for the counter
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.counter_done)

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        self.controller.stop()
        self.live = False
        self.emit_status(ThreadCommand('Update_Status', ['Acquisition stopped.']))
        return ''

    def commit_settings(self, param):
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

        if param.parent() is not None:
            if param.parent().name() == 'ai_channels':
                device = param.opts['title'].split('/')[0]
                self.settings.child('clock_settings', 'frequency').setOpts(max=self.getAIMaxRate(device))

                ranges = self.controller.getAIVoltageRange(device)
                param.child('voltage_settings', 'volt_min').setOpts(limits=[r[0] for r in ranges])
                param.child('voltage_settings', 'volt_max').setOpts(limits=[r[1] for r in ranges])

        DAQ_NIDAQmx_base.commit_settings(self, param)

    def ini_detector(self, controller=None):
        """
            Initialisation procedure of the detector.

            See Also
            --------
            daq_utils.ThreadCommand
        """
        try:
            self.controller = self.ini_detector_init(controller, DAQmx())
            self.update_task()

            # actions to perform in order to set properly the settings tree options
            self.commit_settings(self.settings.child('NIDAQ_type'))

            info = "Plugin Initialized"
            initialized = True
            return info, initialized

        except Exception as e:
            logger.info(traceback.format_exc())
            self.emit_status(ThreadCommand('Update_Status', [str(e), 'log']))
            info = str(e)
            initialized = False
            return info, initialized

    def grab_data(self, Naverage=1, **kwargs):
        """
            | grab the current values with NIDAQ profile procedure.
            |
            | Send the data_grabed_signal once done.

            =============== ======== ===============================================
            **Parameters**  **Type**  **Description**
            *Naverage*      int       Number of values to average
            =============== ======== ===============================================

            See Also
            --------
            DAQ_NIDAQ_source
        """
        update = False

        if 'live' in kwargs:
            if kwargs['live'] != self.live:
                update = True
            self.live = kwargs['live']

        if Naverage != self.Naverage:
            self.Naverage = Naverage
            update = True
        if update:
            self.update_task()

        if self.controller.task is None:
            self.update_task()

        self.controller.register_callback(self.emit_data, "Nsamples", self.clock_settings.Nsamples)
        self.controller.start()

    def emit_data(self, task_handle, every_n_samples_event_type, number_of_samples, callback_data):
        channels_names = [ch.name for ch in self.channels]
        # channels_ai_names = [ch.name for ch in self.channels if ch.source == 'Analog_Input']
        data_from_task = self.controller.task.read(self.settings['nsamplestoread'], timeout=20.0)
        if self.control_type == "0D":
            if not len(self.controller.task.channels.channel_names) != 1:
                data_dfp = [np.array(data_from_task)]
            else:
                data_dfp = list(map(np.array, data_from_task))
            dte = DataToExport(name='NIDAQmx',
                               data=[DataFromPlugins(name='NI Analog Input',
                                                     data=data_dfp,
                                                     dim=f'Data{self.settings.child("display").value()}',
                                                     labels=channels_names
                                                     ),
                                     ])
        self.dte_signal.emit(dte)
        return 0  # mandatory for the NIDAQmx callback

    def counter_done(self):
        channels_name = [ch.name for ch in self.channels]
        data_counter = self.readCounter(len(self.channels),
                                        self.settings['counter_settings', 'counting_time'] * 1e-3)
        self.data_grabed_signal.emit([DataFromPlugins(name='NI Counter', data=[data_counter / 1e-3], dim='Data0D',
                                                      labels=channels_name, )])
        # y_axis=Axis(label='Count Number', units='1/s'))])
        self.task.StopTask()

class DAQ_NIDAQmx_Actuator(DAQ_Move_base, DAQ_NIDAQmx_base):
    """
        Wrapper object to access the Mock fonctionnalities, similar wrapper for all controllers.

        =============== ==============
        **Attributes**    **Type**
        *params*          dictionnary
        =============== ==============
    """
    _controller_units = 'Volts'
    is_multiaxes = False  # set to True if this plugin is controlled for a multiaxis controller (with a unique communication link)
    stage_names = []  # "list of strings of the multiaxes

    params = DAQ_NIDAQmx_base.params + [
        # elements to be added here as dicts in order to control your custom stage
        ############
        {'title': 'MultiAxes:', 'name': 'multiaxes', 'type': 'group', 'visible': is_multiaxes,
         'children': [
             {'title': 'is Multiaxes:', 'name': 'ismultiaxes', 'type': 'bool', 'value': is_multiaxes,
              'default': False},
             {'title': 'Status:', 'name': 'multi_status', 'type': 'list', 'value': 'Master',
              'limits': ['Master', 'Slave']},
             {'title': 'Axis:', 'name': 'axis', 'type': 'list', 'limits': stage_names},
         ]}] + actuator_params

    def __init__(self, parent=None, params_state=None, control_type="Actuator"):
        DAQ_Move_base.__init__(self, parent, params_state)  # defines settings attribute and various other methods
        DAQ_NIDAQmx_base.__init__(self)

        self.control_type = "Actuator"  # could be "0D", "1D" or "Actuator"
        self.settings.child('NIDAQ_type').setLimits(['Analog_Output', 'Digital_Output'])

        self.settings.child('clock_settings', 'Nsamples').setValue(1)

    def get_actuator_value(self) -> DataActuator:
        """Get the current position from the hardware with scaling conversion.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """

        pos = self.target_position
        ##

        pos = self.get_position_with_scaling(pos)
        self.emit_status(ThreadCommand('check_position', [pos]))
        return pos

    def commit_settings(self, param):
        """
            | Activate any parameter changes on the PI_GCS2 hardware.
            |
            | Called after a param_tree_changed signal from DAQ_Move_main.

        """

        DAQ_NIDAQmx_base.commit_settings(self, param)
        if param.name() == 'waveform':
            if param.value() == 'DC':
                self.settings.child('ao_settings', 'cont_param').setValue('offset')
            self.settings.child('ao_settings', 'cont_param').show(not param.value() == 'DC')
            self.settings.child('ao_settings', 'waveform_settings').show(not param.value() == 'DC')

        if param.parent() is not None:
            if param.parent().name() == 'ao_channels':
                device = param.opts['title'].split('/')[0]
                self.settings.child('clock_settings', 'frequency').setOpts(max=self.getAOMaxRate(device))

                ranges = self.getAOVoltageRange(device)
                param.child('voltage_settings', 'volt_min').setOpts(limits=[r[0] for r in ranges])
                param.child('voltage_settings', 'volt_max').setOpts(limits=[r[1] for r in ranges])

    def ini_stage(self, controller=None):
        """Actuator communication initialization

        Parameters
        ----------
        controller: (object) custom object of a PyMoDAQ plugin (Slave case). None if only one actuator by controller (Master case)

        Returns
        -------
        self.status (edict): with initialization status: three fields:
            * info (str)
            * controller (object) initialized controller
            *initialized: (bool): False if initialization failed otherwise True
        """

        try:
            # initialize the stage and its controller status
            # controller is an object that may be passed to other instances of DAQ_Move_Mock in case
            # of one controller controlling multiactuators (or detector)

            self.status.update(edict(info="", controller=None, initialized=False))

            # check whether this stage is controlled by a multiaxe controller (to be defined for each plugin)
            # if multiaxes then init the controller here if Master state otherwise use external controller
            if self.settings['multiaxes', 'ismultiaxes'] and self.settings['multiaxes',
                                                                           'multi_status'] == "Slave":
                if controller is None:
                    raise Exception('no controller has been defined externally while this axe is a slave one')
                else:
                    self.controller = controller
            else:
                self.controller = 'A Nidaqmx task'
                self.update_task()

            # actions to perform in order to set properly the settings tree options
            self.commit_settings(self.settings.child('NIDAQ_type'))

            self.status.info = "Plugin Initialized"
            self.status.controller = self.controller
            self.status.initialized = True
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))
            self.status.info = getLineInfo() + str(e)
            self.status.initialized = False
            return self.status

    def calulate_waveform(self, value):
        waveform = self.settings['ao_settings', 'waveform']
        if waveform == 'DC':
            values = np.array([value])
        else:
            Nsamples = self.settings['clock_settings', 'Nsamples']
            freq = self.settings['clock_settings', 'frequency']
            time = np.linspace(0, Nsamples / freq, Nsamples, endpoint=False)

            freq0 = self.settings['ao_settings', 'waveform_settings', 'frequency']
            amp = self.settings['ao_settings', 'waveform_settings', 'amplitude']
            offset = self.settings['ao_settings', 'waveform_settings', 'offset']
            if waveform == 'Sinus':
                values = offset + amp * np.sin(2 * np.pi * freq0 * time)
            elif waveform == 'Ramp':
                values = offset + amp * np.linspace(0, 1, Nsamples)

        return values

    def move_Abs(self, position):
        """ Move the actuator to the absolute target defined by position

        Parameters
        ----------
        position: (flaot) value of the absolute target positioning
        """

        position = self.check_bound(position)  # if user checked bounds, the defined bounds are applied here
        position = self.set_position_with_scaling(position)  # apply scaling if the user specified one
        if self.settings['NIDAQ_type'] == 'Analog_Output':
            self.settings.child('ao_settings', 'waveform_settings',
                                self.settings['ao_settings', 'cont_param']).setValue(position)
            values = self.calulate_waveform(position)
            self.target_position = position

            self.stop()

            if len(values) == 1:
                self.writeAnalog(len(values), 1, values, autostart=True)
                self.current_position = self.check_position()
                self.move_done()
            else:
                if self.c_callback is None:
                    self.register_callback(self.move_done_callback)
                self.writeAnalog(len(values), 1, values, autostart=False)
                self.task.StartTask()
        elif self.settings['NIDAQ_type'] == 'Digital_Output':
            self.writeDigital(1, np.array([position], dtype=np.uint8), autostart=True)

    def move_done_callback(self, taskhandle, status, callbackdata):
        self.current_position = self.check_position()
        QtWidgets.QApplication.processEvents()
        self.move_done()
        self.task.StopTask()
        return 0

    def move_Rel(self, position):
        """ Move the actuator to the relative target actuator value defined by position

        Parameters
        ----------
        position: (flaot) value of the relative target positioning
        """

        position = self.check_bound(self.current_position + position) - self.current_position
        self.target_position = position + self.current_position
        if self.settings['NIDAQ_type'] == 'Analog_Output':
            self.settings.child('ao_settings', 'waveform_settings',
                                self.settings['ao_settings', 'cont_param']).setValue(self.target_position)

            values = self.calulate_waveform(self.target_position)

            self.stop()

            if len(values) == 1:
                self.writeAnalog(len(values), 1, values, autostart=True)
                self.current_position = self.check_position()
                self.move_done()
            else:
                if self.c_callback is None:
                    self.register_callback(self.move_done_callback)
                self.writeAnalog(len(values), 1, values, autostart=False)
                self.task.StartTask()
        elif self.settings['NIDAQ_type'] == 'Digital_Output':
            self.writeDigital(1, np.array([self.target_position], dtype=np.uint8), autostart=True)

    def move_Home(self):
        """
          Send the update status thread command.
            See Also
            --------
            daq_utils.ThreadCommand
        """

        self.stop()

        if self.c_callback is None:
            self.register_callback(self.move_done_callback)
        self.writeAnalog(1, 1, np.array([0.]))
        self.task.StartTask()

    def stop_motion(self):
        """
          Call the specific move_done function (depending on the hardware).

          See Also
          --------
          move_done
        """

        ## TODO for your custom plugin
        self.stop()
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))
        self.move_done()  # to let the interface know the actuator stopped
        ##############################
