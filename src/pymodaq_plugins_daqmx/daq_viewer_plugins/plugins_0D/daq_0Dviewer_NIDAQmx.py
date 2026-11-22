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
from pymodaq_plugins_daqmx.hardware.national_instruments.save_button import save_param
from pymodaq_gui.utils.status_palette import Status

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
        {'title': 'NIDAQmx config:', 'name': 'config', 'type': 'group', 'children': [
            {'title': 'Configuration:', 'name': 'configuration', 'type': 'list', 'limits': [MANUAL],
             'value': MANUAL},
            save_param(),
        ]},
        {'title': 'Channels:', 'name': 'channels', 'type': 'ni_channels', 'kind': ChannelKind.AI.value,
         'limits': [], 'children': []},
    ]
    data_name = 'NI AI'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings.child('channels').setLimits(NIDAQSystem().all_channels(ChannelKind.AI))
        self.files = ConfigFiles()
        self.loaded = MANUAL  # the configuration whose channels are in the tree
        self.in_file = []  # the channels of that configuration, to tell if the tree still is the file
        self.refresh_menu()

    def refresh_menu(self) -> None:
        self.settings.child('config', 'configuration').setLimits([MANUAL] + [_label(s) for s in self.files.suffixes()])

    def load_configuration(self) -> None:
        """Replace the channels by the ones of the chosen file, in the order of the file.

        The control module is told if it worked (its LED is normal) or not (its LED shows the error).
        """
        label = self.settings['config', 'configuration']
        if not isinstance(label, str):  # a combo that is being rebuilt sends no choice
            return
        if label == MANUAL:  # the channels stay as they are, to be edited by hand
            self.loaded = MANUAL
            self.in_file = []
            return
        try:
            self._load(label)
        except (ValueError, OSError) as error:  # ConfigFileError is a ValueError
            self.settings.child('config', 'configuration').setValue(self.loaded)  # the menu keeps telling the truth
            self.fail(error)

    def _load(self, label: str) -> None:
        configuration = self.files.load(_suffix(label))
        channels = [channel for module in configuration.modules for channel in configuration.channels(module)]
        self.settings.child('channels').setChannels(channels)
        self.loaded = label
        self.in_file = channels
        self.settings.child('config', 'save').setOpts(suffix=label)  # what the dialog of the save button proposes
        self.notify(f'Configuration {label} loaded')

    def save_configuration(self, button: Parameter) -> None:
        """Write the channels of the tree in the file of the suffix given by the dialog of the button.

        The file describes exactly the channels of the tree: each one goes in the module that its name starts with
        (``Dev1`` for ``Dev1/ai1``), as the files name a channel after its module, so that devices can be mixed. In an
        existing file the description, the devices and the notes of the channels that stay are kept.
        """
        suffix = _suffix(button.opts['suffix'])
        channels = self.channels()
        if not channels:
            raise ValueError('There is no channel to save')
        by_module = {}
        for channel in channels:
            by_module.setdefault(channel.name.split('/')[0], []).append(channel)
        configuration = self.files.load(suffix) if self.files.path(suffix).exists() else Configuration()
        for module in [name for name in configuration.modules if name not in by_module]:
            del configuration.modules[module]
        for module, module_channels in by_module.items():
            configuration = configuration.with_channels(module, module_channels)
        self.files.save(suffix, configuration)
        self.refresh_menu()
        self.loaded, self.in_file = _label(suffix), channels  # the tree is that file now
        self.settings.child('config', 'configuration').setValue(self.loaded)
        self.notify(f'Channels saved in the configuration {_label(suffix)}')

    def notify(self, message: str) -> None:
        """Tell the control module that the action succeeded: its LED is back to normal."""
        self.emit_status(ThreadCommand('Update_Status', [message, 'log']))

    def fail(self, error: Exception) -> None:
        """Tell the control module that the action failed: its LED shows the error and its message."""
        self.emit_status(ThreadCommand(ThreadStatus.ERROR, str(error)))

    def channels(self) -> list:
        return channels_of(self.settings.child('channels'))

    def leave_configuration_if_modified(self) -> None:
        """The menu goes back to ``(manual)`` as soon as the channels of the tree are not the ones of the file any more
        (a value that cannot be a channel is a modification too), so that it never shows a configuration that is not
        in the tree, and that choosing the file again reloads it."""
        if self.loaded == MANUAL:
            return
        try:
            same = self.channels() == self.in_file
        except ValueError:
            same = False
        if not same:
            self.loaded = MANUAL
            self.in_file = []
            self.settings.child('config', 'configuration').setValue(MANUAL)

    def own(self, param: Parameter) -> Parameter:
        """The parameter of the tree of this plugin that ``param`` stands for.

        What the GUI changes arrives as its own copy of the parameter, which is not in the tree of the plugin (and
        has not the same parents): what the plugin changes in its tree has to go through this method.
        """
        names = []
        node = param
        while node is not None and node.name() != self.settings.name():
            names.append(node.name())
            node = node.parent()
        if node is None:  # not a parameter of a settings tree
            return param
        return self.settings.child(*reversed(names)) if names else self.settings

    def commit_settings(self, param: Parameter) -> None:
        button = param  # the one of the GUI: it holds what its dialog returned
        param = self.own(param)
        if param.name() == 'configuration' and param.parent() is self.settings.child('config'):
            self.load_configuration()
        elif param.opts['type'] == 'ni_save':  # the button has been clicked, after the dialog of the GUI
            param.opts.update(suffix=button.opts['suffix'])
            try:
                self.save_configuration(param)
                param.setValue(Status.IDLE)
            except (ValueError, OSError) as error:
                param.setValue(Status.ERROR)
                self.fail(error)
        if param.name() == 'type' and param.parent() is not None:
            set_type(ChannelKind.AI, param.parent(), param.value())
        self.leave_configuration_if_modified()
        super().commit_settings(param)


if __name__ == '__main__':
    main(__file__, init=False)
