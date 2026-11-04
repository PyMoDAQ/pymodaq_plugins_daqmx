from easydict import EasyDict as edict
from .daqmxni import NIDAQmx
from pymodaq.utils.data import DataActuator
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
from pymodaq.control_modules.move_utility_classes import comon_parameters_fun as actuator_params
from pymodaq_plugins_daqmx.hardware.national_instruments.NIDAQmx_base import DAQ_NIDAQmx_base
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

    params = DAQ_NIDAQmx_base.params +[
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
        ## TODO: Reimplement in your daq_move with NIDAQmx library
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
        ## TODO: Reimplement in your daq_move with NIDAQmx library
        DAQ_NIDAQmx_base.commit_settings(self, param)
        if param.parent() is not None:
            if param.parent().name() == 'ao_channels':
                device = param.opts['title'].split('/')[0]
                self.settings.child('clock_settings', 'frequency').setOpts(max=self.getAOMaxRate(device))

                volt_ranges = self.controller.getAOVoltageRange(device)
                curr_ranges = self.controller.getA0CurrentRange(device)
                try:
                    param.child('voltage_settings', 'volt_min').setValue(volt_ranges[0])
                    param.child('voltage_settings', 'volt_max').setValue(volt_ranges[1])
                    param.child('current_settings', 'curr_min').setValue(curr_ranges[0])
                    param.child('current_settings', 'curr_max').setValue(curr_ranges[1])
                except:
                    pass

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
            * initialized: (bool): False if initialization failed otherwise True

        """
        try:
            # initialize the stage and its controller status
            # controller is an object that may be passed to other instances of DAQ_Move_Mock in case
            # of one controller controlling multiactuators (or detector)

            self.status.update(edict(info="", controller=None, initialized=False))

            # check whether this stage is controlled by a multiaxe controller (to be defined for each plugin)
            # if multiaxes then init the controller here if Master state otherwise use external controller
            if self.is_multiaxes and not self.is_master:
                if controller is None:
                    raise Exception('no controller has been defined externally while this axe is a slave one')
                else:
                    self.controller = controller
            else:
                self.controller = NIDAQmx()

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

    def move_Abs(self, position):
        """ Move the actuator to the absolute target defined by position

        Parameters
        ----------
        position: (flaot) value of the absolute target positioning
        """
        ## TODO: Reimplement in your daq_move with NIDAQmx library
        raise NotImplementedError

    def move_done_callback(self, taskhandle, status, callbackdata):
        ## TODO: Reimplement in your daq_move with NIDAQmx library
        raise NotImplementedError

    def move_Rel(self, position):
        """ Move the actuator to the relative target actuator value defined by position

        Parameters
        ----------
        position: (flaot) value of the relative target positioning
        """
        ## TODO: Reimplement in your daq_move with NIDAQmx library
        raise NotImplementedError

    def move_Home(self):
        """
          Send the update status thread command.
            See Also
            --------
            daq_utils.ThreadCommand
        """
        ## TODO: Reimplement in your daq_move with NIDAQmx library
        raise NotImplementedError

    def stop_motion(self):
        """
          Call the specific move_done function (depending on the hardware).

          See Also
          --------
          move_done
        """
        """Stop the current grab hardware wise if necessary"""
        try:
            DAQ_NIDAQmx_base.stop(self)
            self.move_done()  # to let the interface know the actuator stopped
            logger.info("Motion stopped.")
        except Exception:
            pass
        self.emit_status(ThreadCommand('Update_Status', ['Motion stopped.']))
        return ''
