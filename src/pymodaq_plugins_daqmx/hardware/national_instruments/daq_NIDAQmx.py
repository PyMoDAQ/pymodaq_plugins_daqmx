from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal, QThread
from pymodaq.daq_utils.daq_utils import ThreadCommand, DataFromPlugins, Axis, getLineInfo
import numpy as np
from pymodaq.daq_viewer.utility_classes import DAQ_Viewer_base
from pymodaq.daq_move.utility_classes import DAQ_Move_base
from easydict import EasyDict as edict
from abc import ABC, abstractmethod

from pymodaq.daq_viewer.utility_classes import comon_parameters as viewer_params
from pymodaq.daq_move.utility_classes import comon_parameters as actuator_params

from pyqtgraph.parametertree import Parameter, ParameterTree, registerParameterType
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.parameter.pymodaq_ptypes as pymodaq_ptypes

from .daqmx import DAQmx, DAQ_analog_types, DAQ_thermocouples, DAQ_termination, Edge, DAQ_NIDAQ_source, \
    ClockSettings, AIChannel, Counter, AIThermoChannel, AOChannel, TriggerSettings


class ScalableGroupAI(custom_tree.GroupParameterCustom):
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

    params = [{'title': 'AI type:', 'name': 'ai_type', 'type': 'list', 'values': DAQ_analog_types.names()},
              {'title': 'Voltages:', 'name': 'voltage_settings', 'type': 'group', 'children': [
                  {'title': 'Voltage Min:', 'name': 'volt_min', 'type': 'list', 'value': -10.},
                  {'title': 'Voltage Max:', 'name': 'volt_max', 'type': 'list', 'value': 10.},
              ]},
              {'title': 'Current:', 'name': 'current_settings', 'type': 'group', 'visible': False, 'children': [
                  {'title': 'Current Min:', 'name': 'curr_min', 'type': 'float', 'value': -1, 'suffix': 'A'},
                  {'title': 'Current Max:', 'name': 'curr_max', 'type': 'float', 'value': 1, 'suffix': 'A'},
              ]},
              {'title': 'Thermocouple:', 'name': 'thermoc_settings', 'type': 'group', 'visible': False, 'children': [
                  {'title': 'Thc. type:', 'name': 'thermoc_type', 'type': 'list', 'values': DAQ_thermocouples.names(),
                   'value': 'K'},
                  {'title': 'Temp. Min (°C):', 'name': 'T_min', 'type': 'float', 'value': 0, 'suffix': '°C'},
                  {'title': 'Temp. Max (°C):', 'name': 'T_max', 'type': 'float', 'value': 50, 'suffix': '°C'},
              ]},
              {'title': 'Termination:', 'name': 'termination', 'type': 'list', 'values': DAQ_termination.names()},
              ]

    def __init__(self, **opts):
        opts['type'] = 'groupai'
        opts['addText'] = "Add"
        opts['addList'] = opts['values']
        pTypes.GroupParameter.__init__(self, **opts)

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


class ScalableGroupAO(custom_tree.GroupParameterCustom):
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

    params = [{'title': 'AO type:', 'name': 'ao_type', 'type': 'list', 'values': DAQ_analog_types.names()[0:2]},
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
        opts['addList'] = opts['values']
        pTypes.GroupParameter.__init__(self, **opts)

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


class ScalableGroupCounter(custom_tree.GroupParameterCustom):
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

    params = [{'title': 'Edge type:', 'name': 'edge', 'type': 'list', 'values': Edge.names()}, ]

    def __init__(self, **opts):
        opts['type'] = 'groupcounter'
        opts['addText'] = "Add"
        opts['addList'] = opts['values']
        pTypes.GroupParameter.__init__(self, **opts)

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


class DAQ_NIDAQmx_base(DAQmx):
    data_grabed_signal = pyqtSignal(list)

    params =[{'title': 'Refresh hardware:', 'name': 'refresh_hardware', 'type': 'bool', 'value': False},
            {'title': 'Signal type:', 'name': 'NIDAQ_type', 'type': 'list', 'values': DAQ_NIDAQ_source.names()},
             {'title': 'AO Settings:', 'name': 'ao_settings', 'type': 'group', 'children': [
                 {'title': 'Waveform:', 'name': 'waveform', 'type': 'list', 'value': 'DC', 'values': ['DC', 'Sinus', 'Ramp']},
                 {'title': 'Repetition?:', 'name': 'repetition', 'type': 'bool', 'value': False, },
                 {'title': 'Controlled param:', 'name': 'cont_param', 'type': 'list', 'value': 'offset',
                  'values': ['offset', 'amplitude', 'frequency']},
                 {'title': 'Waveform Settings:', 'name': 'waveform_settings', 'type': 'group', 'visible': False, 'children': [
                     {'title': 'Offset:', 'name': 'offset', 'type': 'float', 'value': 0., },
                     {'title': 'Amplitude:', 'name': 'amplitude', 'type': 'float', 'value': 1., },
                     {'title': 'Frequency:', 'name': 'frequency', 'type': 'float', 'value': 10., },
                    ]},
             ]},
            {'title': 'Clock Settings:', 'name': 'clock_settings', 'type': 'group', 'children': [
                {'title': 'Nsamples:', 'name': 'Nsamples', 'type': 'int', 'value': 1000, 'default': 1000, 'min': 1},
                {'title': 'Frequency:', 'name': 'frequency', 'type': 'float', 'value': 1000., 'default': 1000.,
                 'min': 0., 'suffix': 'Hz'},
            ]
            },
            {'title': 'AI Channels:', 'name': 'ai_channels', 'type': 'groupai',
                  'values': DAQmx.get_NIDAQ_channels(source_type='Analog_Input')},
            {'title': 'AO Channels:', 'name': 'ao_channels', 'type': 'groupao',
                 'values': DAQmx.get_NIDAQ_channels(source_type='Analog_Output')},
            {'title': 'Counter Settings:', 'name': 'counter_settings', 'type': 'group', 'visible': True, 'children': [
                {'title': 'Counting time (ms):', 'name': 'counting_time', 'type': 'float', 'value': 100.,
                'default': 100., 'min': 0.},
                {'title': 'Counting Channels:', 'name': 'counter_channels', 'type': 'groupcounter',
                'values': DAQmx.get_NIDAQ_channels(source_type='Counter')},
            ]},
            {'title': 'Trigger Settings:', 'name': 'trigger_settings', 'type': 'group', 'visible': True, 'children': [
                {'title': 'Enable?:', 'name': 'enable', 'type': 'bool', 'value': False, },
                {'title': 'Trigger Source:', 'name': 'trigger_channel', 'type': 'list',
                 'values': DAQmx.getTriggeringSources()},
                {'title': 'Edge type:', 'name': 'edge', 'type': 'list', 'values': Edge.names(), 'visible': False},
                {'title': 'Level:', 'name': 'level', 'type': 'float', 'value': 1., 'visible': False}
                ]}
            ]

    def __init__(self):
        super().__init__()

        self.timer = None
        self.channels = None
        self.clock_settings = None
        self.trigger_settings = None
        self.refresh_hardware()


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
        # if param.name() == 'NIDAQ_devices':
        #     self.update_NIDAQ_channels()
        #     self.update_task()

        if param.name() == 'NIDAQ_type':
            self.update_NIDAQ_channels(param.value())
            if param.value() == DAQ_NIDAQ_source(0).name: #analog input
                self.settings.child(('clock_settings')).show()
                self.settings.child(('ai_channels')).show()
                self.settings.child(('ao_channels')).hide()
                self.settings.child(('ao_settings')).hide()
                self.settings.child(('counter_settings')).hide()

            elif param.value() == DAQ_NIDAQ_source(1).name: #counter input
                self.settings.child(('clock_settings')).hide()
                self.settings.child(('ai_channels')).hide()
                self.settings.child(('ao_channels')).hide()
                self.settings.child(('ao_settings')).hide()
                self.settings.child(('counter_settings')).show()

            elif param.value() == DAQ_NIDAQ_source(2).name: #analog output
                self.settings.child(('clock_settings')).show()
                self.settings.child(('ai_channels')).hide()
                self.settings.child(('ao_channels')).show()
                self.settings.child(('ao_settings')).show()
                self.settings.child(('counter_settings')).hide()
            self.update_task()

        elif param.name() == 'refresh_hardware':
            if param.value():
                self.refresh_hardware()
                QtWidgets.QApplication.processEvents()
                self.settings.child(('refresh_hardware')).setValue(False)

        elif param.name() == 'ai_type':
            param.parent().child(('voltage_settings')).show(param.value() == 'Voltage')
            param.parent().child(('current_settings')).show(param.value() == 'Current')
            param.parent().child(('thermoc_settings')).show(param.value() == 'Thermocouple')
            self.update_task()

        elif param.name() == 'ao_type':
            param.parent().child(('voltage_settings')).show(param.value() == 'Voltage')
            param.parent().child(('current_settings')).show(param.value() == 'Current')
            self.update_task()

        elif param.name() == 'trigger_channel':
            param.parent().child('level').show('PF' not in param.opts['title'])

        else:
            self.update_task()


    def update_task(self):
        self.channels = self.get_channels_from_settings()
        self.clock_settings = ClockSettings(frequency=self.settings.child('clock_settings', 'frequency').value(),
                                            Nsamples=self.settings.child('clock_settings', 'Nsamples').value(),
                                            repetition=self.settings.child('ao_settings', 'repetition').value(),)
        self.trigger_settings = \
            TriggerSettings(trig_source=self.settings.child('trigger_settings', 'trigger_channel').value(),
                            enable=self.settings.child('trigger_settings', 'enable').value(),
                            edge=self.settings.child('trigger_settings', 'edge').value(),
                            level=self.settings.child('trigger_settings', 'level').value(),)

        if not not self.channels:
            super().update_task(self.channels, self.clock_settings, trigger_settings=self.trigger_settings)


    def get_channels_from_settings(self):
        channels = []
        if self.settings.child(('NIDAQ_type')).value() == DAQ_NIDAQ_source(0).name:  # analog input
            for channel in self.settings.child('ai_channels').children():
                analog_type = channel.child('ai_type').value()
                if analog_type == 'Voltage':
                    channels.append(AIChannel(name=channel.opts['title'],
                                              source='Analog_Input', analog_type=analog_type,
                                              value_min=channel.child('voltage_settings', 'volt_min').value(),
                                              value_max=channel.child('voltage_settings', 'volt_max').value(),
                                              termination=channel.child('termination').value(),))
                elif analog_type == 'Current':
                    channels.append(AIChannel(name=channel.opts['title'],
                                              source='Analog_Input', analog_type=analog_type,
                                              value_min=channel.child('current_settings', 'curr_min').value(),
                                              value_max=channel.child('current_settings', 'curr_max').value(),
                                              termination=channel.child('termination').value(), ))
                elif analog_type == 'Thermocouple':
                    channels.append(AIThermoChannel(name=channel.opts['title'],
                                              source='Analog_Input', analog_type=analog_type,
                                              value_min=channel.child('thermoc_settings', 'T_min').value(),
                                              value_max=channel.child('thermoc_settings', 'T_max').value(),
                                              termination=channel.child('termination').value(),
                                              thermo_type=channel.child('thermoc_settings', 'thermoc_type').value(),))

        elif self.settings.child(('NIDAQ_type')).value() == DAQ_NIDAQ_source(1).name:  # counter input
            for channel in self.settings.child('counter_settings', 'counter_channels').children():
                channels.append(Counter(name=channel.opts['title'],
                                        source='Counter', edge=channel.child('edge').value()))

        elif self.settings.child(('NIDAQ_type')).value() == DAQ_NIDAQ_source(2).name:  # analog output
            for channel in self.settings.child('ao_channels').children():
                analog_type = channel.child('ao_type').value()
                channels.append(AOChannel(name=channel.opts['title'],
                                          source='Analog_Output', analog_type=analog_type,
                                          value_min=channel.child('voltage_settings', 'volt_min').value(),
                                          value_max=channel.child('voltage_settings', 'volt_max').value(),
                                          ))

        return channels

    def stop(self):
        """
        """
        if not not self.timer:
            self.timer.stop()
        QtWidgets.QApplication.processEvents()
        DAQmx.stop(self)


class DAQ_NIDAQmx_Viewer(DAQ_Viewer_base, DAQ_NIDAQmx_base):
    """
        ==================== ========================
        **Attributes**         **Type**
        *data_grabed_signal*   instance of pyqtSignal
        *params*               dictionnary list
        *task*
        ==================== ========================

        See Also
        --------
        refresh_hardware
    """

    data_grabed_signal = pyqtSignal(list)

    params = viewer_params + DAQ_NIDAQmx_base.params

    def __init__(self, parent=None, params_state=None, control_type="0D"):
        DAQ_Viewer_base.__init__(self, parent, params_state) #defines settings attribute and various other methods
        DAQ_NIDAQmx_base.__init__(self)


        self.control_type = control_type  # could be "0D", "1D" or "Actuator"
        if self.control_type == "0D":
            self.settings.child(('NIDAQ_type')).setLimits(DAQ_NIDAQ_source.names()[0:2])  # analog input and counter
        elif self.control_type == "1D":
            self.settings.child(('NIDAQ_type')).setLimits(['Analog_Input'])
        elif self.control_type == "Actuator":
            self.settings.child(('NIDAQ_type')).setLimits(['Analog_Output'])



        self.settings.child('ao_channels').hide()

        #timer used for the counter
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.counter_done)




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

                ranges = self.getAIVoltageRange(device)
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
        self.status.update(edict(initialized=False, info="", x_axis=None, y_axis=None, controller=None))
        try:
            if self.settings.child(('controller_status')).value() == "Slave":
                if controller is None:
                    raise Exception('no controller has been defined externally while this detector is a slave one')
                else:
                    self.controller = 'A Nidaqmx task'
            else:
                self.update_task()

            #actions to perform in order to set properly the settings tree options
            self.commit_settings(self.settings.child('NIDAQ_type'))

            self.status.info = "Plugin Initialized"
            self.status.initialized = True
            self.status.controller = controller
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [str(e), 'log']))
            self.status.info = str(e)
            self.status.initialized = False
            return self.status

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
        if self.settings.child(('NIDAQ_type')).value() == DAQ_NIDAQ_source(0).name: #analog input
            if self.c_callback is None:
                self.register_callback(self.emit_data)
        elif self.settings.child(('NIDAQ_type')).value() == DAQ_NIDAQ_source(1).name: #counter input
            self.timer.start(self.settings.child('counter_settings', 'counting_time').value())
        self.task.StartTask()

    def emit_data(self, taskhandle, status, callbackdata):
        channels_name = [ch.name for ch in self.channels]

        data_tot = []
        data = self.readAnalog(len(self.channels), self.clock_settings)
        N = self.clock_settings.Nsamples
        if self.control_type == "0D":
            for ind in range(len(self.channels)):
                data_tot.append(np.array([np.mean(data[ind*N:(ind+1)*N])]))
            self.data_grabed_signal.emit([DataFromPlugins(name='NI AI', data=data_tot, dim='Data0D',
                                          labels=channels_name)])
        else:
            for ind in range(len(self.channels)):
                data_tot.append(data[ind*N:(ind+1)*N])
            self.data_grabed_signal.emit([DataFromPlugins(name='NI AI', data=data_tot, dim='Data1D',
                                          labels=channels_name,
                                          x_axis=Axis(data=np.linspace(0, N / self.clock_settings.frequency, N),
                                          y_axis=Axis(label='Analog Input', units=''),
                                          label='Time', units='s'))])

        self.task.StopTask()

        return 0  #mandatory for the PyDAQmx callback



    def counter_done(self):
        channels_name = [ch.name for ch in self.channels]
        data_counter = self.readCounter(len(self.channels),
                                        self.settings.child('counter_settings', 'counting_time').value() * 1e-3)
        self.data_grabed_signal.emit([DataFromPlugins(name='NI Counter', data=[data_counter / 1e-3], dim='Data0D',
                                                      labels=channels_name,
                                      y_axis=Axis(label='Count Number', units='1/s'))])
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

    params = DAQ_NIDAQmx_base.params +[
              # elements to be added here as dicts in order to control your custom stage
              ############
              {'title': 'MultiAxes:', 'name': 'multiaxes', 'type': 'group', 'visible': is_multiaxes,
               'children': [
                   {'title': 'is Multiaxes:', 'name': 'ismultiaxes', 'type': 'bool', 'value': is_multiaxes,
                    'default': False},
                   {'title': 'Status:', 'name': 'multi_status', 'type': 'list', 'value': 'Master',
                    'values': ['Master', 'Slave']},
                   {'title': 'Axis:', 'name': 'axis', 'type': 'list', 'values': stage_names},

               ]}] + actuator_params

    def __init__(self, parent=None, params_state=None, control_type="Actuator"):
        DAQ_Move_base.__init__(self, parent, params_state)  # defines settings attribute and various other methods
        DAQ_NIDAQmx_base.__init__(self)

        self.control_type = "Actuator"  # could be "0D", "1D" or "Actuator"
        self.settings.child(('NIDAQ_type')).setLimits(['Analog_Output'])

        self.settings.child('clock_settings', 'Nsamples').setValue(1)

        self.settings.child('NIDAQ_type').hide()


    def check_position(self):
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
            if self.settings.child('multiaxes', 'ismultiaxes').value() and self.settings.child('multiaxes',
                                                                              'multi_status').value() == "Slave":
                if controller is None:
                    raise Exception('no controller has been defined externally while this axe is a slave one')
                else:
                    self.controller = 'A Nidaqmx task'
            else:
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
        waveform = self.settings.child('ao_settings', 'waveform').value()
        if waveform == 'DC':
            values = np.array([value])
        else:
            Nsamples = self.settings.child('clock_settings', 'Nsamples').value()
            freq = self.settings.child('clock_settings', 'frequency').value()
            time = np.linspace(0, Nsamples / freq, Nsamples, endpoint=False)

            freq0 = self.settings.child('ao_settings', 'waveform_settings', 'frequency').value()
            amp = self.settings.child('ao_settings', 'waveform_settings', 'amplitude').value()
            offset = self.settings.child('ao_settings', 'waveform_settings', 'offset').value()
            if waveform == 'Sinus':
                values = offset + amp * np.sin(2*np.pi*freq0*time)
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

        self.settings.child('ao_settings', 'waveform_settings',
                             self.settings.child('ao_settings', 'cont_param').value()).setValue(position)
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

        self.settings.child('ao_settings', 'waveform_settings',
                             self.settings.child('ao_settings', 'cont_param').value()).setValue(self.target_position)

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

