from typing import List, Optional

from pymodaq.control_modules.thread_commands import ThreadStatus
from pymodaq.control_modules.viewer_utility_classes import main
from pymodaq.utils.daq_utils import ThreadCommand
from pyqtgraph.parametertree import Parameter

from pymodaq_plugins_daqmx.hardware.national_instruments.NIDAQmx_AI import DAQ_Viewer_AIBase
from pymodaq_plugins_daqmx.hardware.national_instruments.api import ChannelKind, NIDAQSystem
from pymodaq_plugins_daqmx.hardware.national_instruments.channel_group import channels_of
from pymodaq_plugins_daqmx.hardware.national_instruments.channel_tree import set_type
from pymodaq_plugins_daqmx.hardware.national_instruments.config_files import Configuration, ConfigFiles

MANUAL = '(manual)'    # no configuration file: the channels are the ones of the tree
DEFAULT = 'default'    # the name of the configuration of the file without suffix


def _label(suffix: str) -> str:
    return suffix or DEFAULT


def _suffix(label: str) -> str:
    return '' if label == DEFAULT else label


class DAQ_0DViewer_NIDAQmx(DAQ_Viewer_AIBase):
    """Analog inputs of any NI device, as 0D (mean value) or 1D (trace) data.

    The channels are added to the `channels` group of the settings, each with the parameters of its type of channel.
    """
    params = DAQ_Viewer_AIBase.params + [
        {'title': 'Configuration:', 'name': 'configuration', 'type': 'list', 'limits': [MANUAL], 'value': MANUAL},
        {'title': 'Module:', 'name': 'module', 'type': 'list', 'limits': [], 'visible': False},
        {'title': 'Channels:', 'name': 'channels', 'type': 'ni_channels', 'kind': ChannelKind.AI.value,
         'limits': [], 'children': []},
        {'title': 'Save as:', 'name': 'save', 'type': 'group', 'children': [
            {'title': 'Suffix:', 'name': 'suffix', 'type': 'str', 'value': DEFAULT},
            {'title': 'Module:', 'name': 'module', 'type': 'str', 'value': ''},
            {'title': 'Save', 'name': 'save', 'type': 'bool_push', 'value': False},
        ]},
    ]
    data_name = 'NI AI'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings.child('channels').setLimits(NIDAQSystem().all_channels(ChannelKind.AI))
        self.files = ConfigFiles()
        self.loaded = (MANUAL, '')  # the configuration and the module whose channels are in the tree
        self.refresh_menu()

    def refresh_menu(self) -> None:
        self.settings.child('configuration').setLimits([MANUAL] + [_label(s) for s in self.files.suffixes()])

    def load_configuration(self) -> None:
        """Read the chosen file, offer its modules and replace the channels by the ones of the chosen module.

        The control module is told if it worked (its LED is normal) or not (its LED shows the error).
        """
        label = self.settings['configuration']
        if label == MANUAL:  # the channels stay as they are, to be edited by hand
            self.loaded = (MANUAL, '')
            self.settings.child('module').setOpts(visible=False)
            return
        try:
            self._load(label)
        except (ValueError, OSError) as error:  # ConfigFileError is a ValueError
            self.show_loaded()  # the menu keeps telling the truth
            self.fail(error)

    def show_loaded(self) -> None:
        """Put the menus back on what is really loaded."""
        configuration, module = self.loaded
        self.settings.child('configuration').setValue(configuration)
        self.settings.child('module').setOpts(visible=configuration != MANUAL)
        if module:
            self.settings.child('module').setValue(module)

    def _load(self, label: str) -> None:
        configuration = self.files.load(_suffix(label))
        modules = list(configuration.modules)
        module = self.settings.child('module')
        module.setOpts(limits=modules, visible=True)
        if self.settings['module'] not in modules:
            module.setValue(modules[0] if modules else '')
        self.settings.child('channels').setChannels(configuration.channels(self.settings['module']))
        self.loaded = (label, self.settings['module'])
        self.notify(f'Configuration {label}, module {self.settings["module"]} loaded')

    def save_configuration(self) -> None:
        """Write the channels of the tree as the module of the suffix, keeping the rest of that file if it exists."""
        suffix = _suffix(self.settings['save', 'suffix'])
        module = self.settings['save', 'module']
        if not module:
            raise ValueError('Give the name of the module that the channels belong to')
        existing = self.files.load(suffix) if self.files.path(suffix).exists() else Configuration()
        self.files.save(suffix, existing.with_channels(module, self.channels()))
        self.refresh_menu()
        self.notify(f'Channels saved as the module {module} of the configuration {_label(suffix)}')

    def notify(self, message: str) -> None:
        """Tell the control module that the action succeeded: its LED is back to normal."""
        self.emit_status(ThreadCommand('Update_Status', [message, 'log']))

    def fail(self, error: Exception) -> None:
        """Tell the control module that the action failed: its LED shows the error and its message."""
        self.emit_status(ThreadCommand(ThreadStatus.ERROR, str(error)))

    def channels(self) -> list:
        return channels_of(self.settings.child('channels'))

    def commit_settings(self, param: Parameter) -> None:
        if param.name() in ('configuration', 'module') and param.parent() is self.settings:
            self.load_configuration()
        elif param.opts['type'] == 'bool_push' and param.value():
            param.setValue(False)
            try:
                self.save_configuration()
            except (ValueError, OSError) as error:
                self.fail(error)
        if param.name() == 'type' and param.parent() is not None:
            set_type(ChannelKind.AI, param.parent(), param.value())
        super().commit_settings(param)


if __name__ == '__main__':
    main(__file__, init=False)
