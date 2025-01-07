import numpy as np
from easydict import EasyDict as edict
from qtpy import QtWidgets
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters as actuator_params
from pymodaq_plugins_daqmx.hardware.national_instruments.daq_NIDAQmx import DAQ_NIDAQmx_base
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from pymodaq.utils.data import DataActuator
from pymodaq.utils.logger import set_logger, get_module_name
logger = set_logger(get_module_name(__file__))


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
         ]}] + actuator_params()

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
        self.status (easydict): with initialization status: three fields:
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

    def move_abs(self, position):
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

    def move_rel(self, position):
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

    def move_home(self):
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
