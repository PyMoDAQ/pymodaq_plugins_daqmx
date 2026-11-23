from typing import List, Optional

from pymodaq.control_modules.thread_commands import ThreadStatus
from pymodaq.control_modules.viewer_utility_classes import main
from pymodaq.utils.daq_utils import ThreadCommand
from pyqtgraph.parametertree import Parameter

from pymodaq_plugins_daqmx.hardware.national_instruments.NIDAQmx_AI import Acquisition, DAQ_Viewer_AIBase
from nidaqmx.constants import Edge, Slope

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AnalogEdgeTrigger, ChannelKind, DigitalEdgeTrigger, NIDAQSystem)
from pymodaq_plugins_daqmx.hardware.national_instruments.channel_group import channels_of, unread_of
from pymodaq_plugins_daqmx.hardware.national_instruments.channel_tree import set_type
from pymodaq_plugins_daqmx.hardware.national_instruments.config_files import Configuration, ConfigFiles
from pymodaq_plugins_daqmx.hardware.national_instruments.save_button import save_param
from pymodaq_gui.utils.status_palette import Status

MANUAL = '(manual)'    # no configuration file: the channels are the ones of the tree
TRIGGER_TYPES = ['none', 'digital edge', 'analog edge']
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
        {'title': 'Start trigger:', 'name': 'trigger', 'type': 'group', 'children': [
            {'title': 'Type:', 'name': 'type', 'type': 'list', 'limits': TRIGGER_TYPES, 'value': 'none'},
            {'title': 'Terminal:', 'name': 'terminal', 'type': 'list', 'limits': [], 'visible': False},
            {'title': 'Channel:', 'name': 'channel', 'type': 'list', 'limits': [], 'visible': False},
            {'title': 'Edge:', 'name': 'edge', 'type': 'list', 'limits': ['rising', 'falling'], 'value': 'rising',
             'visible': False},
            {'title': 'Level (V):', 'name': 'level', 'type': 'float', 'value': 0., 'visible': False},
        ]},
        {'title': 'Module frequencies:', 'name': 'frequencies', 'type': 'group', 'children': []},
        {'title': 'Channels:', 'name': 'channels', 'type': 'ni_channels', 'kind': ChannelKind.AI.value,
         'limits': [], 'children': []},
    ]
    data_name = 'NI AI'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        system = NIDAQSystem()
        self.settings.child('channels').setLimits(system.all_channels(ChannelKind.AI))
        self.settings.child('trigger', 'terminal').setLimits(
            [terminal for device in system.devices() for terminal in system.terminals(device)])
        self.files = ConfigFiles()
        self.loaded = MANUAL  # the configuration whose channels are in the tree
        self.in_file = ()  # what the file describes (see `snapshot`), to tell if the tree still is the file
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
            self.in_file = ()
            return
        try:
            self._load(label)
        except (ValueError, OSError) as error:  # ConfigFileError is a ValueError
            self.settings.child('config', 'configuration').setValue(self.loaded)  # the menu keeps telling the truth
            self.fail(error)

    def _load(self, label: str) -> None:
        configuration = self.files.load(_suffix(label))
        channels = [channel for module in configuration.modules for channel in configuration.channels(module)]
        unread = {name for module in configuration.modules for name in configuration.unread(module)}
        self.settings.child('channels').setChannels(channels, unread)
        self.sync_frequencies()
        self.sync_trigger_channels()
        for module in self.modules():  # a module that the file gives no frequency to goes back to the global one
            frequency = configuration.frequency(module) or self.settings['frequency']
            self.settings.child('frequencies', module).setValue(frequency)
        self.set_trigger(configuration.trigger)
        self.loaded = label
        self.in_file = self.snapshot()
        self.settings.child('config', 'save').setOpts(suffix=label)  # what the dialog of the save button proposes
        self.notify(f'Configuration {label} loaded')

    def save_configuration(self, button: Parameter) -> None:
        """Write the channels of the tree in the file of the suffix given by the dialog of the button.

        The file describes exactly the channels of the tree: each one goes in the module that its name starts with
        (``Dev1`` for ``Dev1/ai1``), as the files name a channel after its module, so that devices can be mixed. In an
        existing file the description, the devices and the notes of the channels that stay are kept.
        """
        suffix = _suffix(button.opts['suffix'])
        self.sync_frequencies()
        channels = self.channels()
        if not channels:
            raise ValueError('There is no channel to save')
        unread = unread_of(self.settings.child('channels'))
        by_module = {}
        for channel in channels:
            by_module.setdefault(channel.name.split('/')[0], []).append(channel)
        configuration = self.files.load(suffix) if self.files.path(suffix).exists() else Configuration()
        for module in [name for name in configuration.modules if name not in by_module]:
            del configuration.modules[module]
        for module, module_channels in by_module.items():
            configuration = configuration.with_channels(
                module, module_channels, unread=[c.name for c in module_channels if c.name in unread])
            configuration = configuration.with_frequency(module, self.settings['frequencies', module])
        self.files.save(suffix, configuration.with_trigger(self.trigger_keys()))
        self.refresh_menu()
        self.loaded, self.in_file = _label(suffix), self.snapshot()  # the tree is that file now
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

    def modules(self) -> List[str]:
        """The modules of the channels of the tree (the device a channel name starts with), in order of appearance."""
        names = [child.opts['title'].split('/')[0] for child in self.settings.child('channels').children()]
        return list(dict.fromkeys(names))

    def sync_trigger_channels(self) -> None:
        """What an analog trigger can watch: the channels of the tree (the driver only accepts a channel of the task)
        and the dedicated analog trigger terminals (``/Dev1/APFI0``) of the devices of the tree, which are not read."""
        names = [child.opts['title'] for child in self.settings.child('channels').children()]
        system = NIDAQSystem()
        for module in self.modules():
            try:
                names += [t for t in system.terminals(module) if '/APFI' in t]
            except ValueError:  # a module that is not a device of the system
                pass
        channel = self.settings.child('trigger', 'channel')
        if channel.opts['limits'] != names:
            channel.setLimits(names)

    def sync_frequencies(self) -> None:
        """One frequency for each module of the channels: a new module starts at the global frequency."""
        group = self.settings.child('frequencies')
        modules = self.modules()
        for child in group.children():
            if child.name() not in modules:
                group.removeChild(child)
        for module in modules:
            if module not in group.names:
                group.addChild({'title': f'{module}:', 'name': module, 'type': 'int', 'min': 1,
                                'value': self.settings['frequency']})

    def trigger_for(self, acquisition: Acquisition):
        """The start trigger chosen in the settings for the task of ``acquisition``, or None. A digital trigger starts
        every task; an analog one watches a channel of its task, so it starts only the task of that channel."""
        settings = self.settings.child('trigger')
        kind = settings['type']
        if kind == 'digital edge':
            return DigitalEdgeTrigger(settings['terminal'], Edge[settings['edge'].upper()])
        source = settings['channel']
        if kind == 'analog edge' and (source in acquisition.labels or source.startswith(f'/{acquisition.name}/')):
            return AnalogEdgeTrigger(settings['channel'], settings['level'], Slope[settings['edge'].upper()])
        return None

    def trigger_keys(self) -> Optional[dict]:
        """The start trigger of the tree as the keys of the ``[trigger]`` table of a file, or None."""
        settings = self.settings.child('trigger')
        if settings['type'] == 'digital edge':
            return {'type': 'digital edge', 'terminal': settings['terminal'], 'edge': settings['edge']}
        if settings['type'] == 'analog edge':
            return {'type': 'analog edge', 'channel': settings['channel'], 'level': settings['level'],
                    'edge': settings['edge']}
        return None

    def set_trigger(self, keys: Optional[dict]) -> None:
        """Put the trigger of a file in the tree (no trigger if the file has none)."""
        settings = self.settings.child('trigger')
        keys = keys or {'type': 'none'}
        settings.child('type').setValue(keys['type'])
        for key in ('terminal', 'channel', 'level'):
            if key in keys:
                settings.child(key).setValue(keys[key])
        settings.child('edge').setValue(keys.get('edge', 'rising'))
        self.show_trigger()

    def snapshot(self) -> tuple:
        """What a configuration file describes in the tree: the channels, the frequency of each module and the
        trigger."""
        self.sync_frequencies()
        frequencies = tuple((child.name(), child.value()) for child in self.settings.child('frequencies').children())
        return tuple(self.channels()), tuple(unread_of(self.settings.child('channels'))), frequencies, self.trigger_keys()

    def show_trigger(self) -> None:
        """Only the parameters of the chosen type of trigger are visible."""
        settings = self.settings.child('trigger')
        kind = settings['type']
        settings.child('terminal').setOpts(visible=kind == 'digital edge')
        settings.child('channel').setOpts(visible=kind == 'analog edge')
        settings.child('level').setOpts(visible=kind == 'analog edge')
        settings.child('edge').setOpts(visible=kind != 'none')

    def acquisitions(self) -> List[Acquisition]:
        """One task for each module: the channels of a module are acquired together, at its own frequency."""
        self.sync_frequencies()  # the channels may have been added without the GUI telling the plugin
        self.sync_trigger_channels()
        by_module = {}
        for channel in self.channels():
            by_module.setdefault(channel.name.split('/')[0], []).append(channel)
        unread = unread_of(self.settings.child('channels'))
        return [Acquisition(module, channels, self.settings['frequencies', module],
                            tuple(c.name for c in channels if c.name in unread))
                for module, channels in by_module.items()]

    def leave_configuration_if_modified(self) -> None:
        """The menu goes back to ``(manual)`` as soon as the tree is not what the file describes any more: its
        channels, the frequencies of the modules or the trigger (a value that cannot be a channel is a modification too), so that it never shows a configuration that is not
        in the tree, and that choosing the file again reloads it."""
        if self.loaded == MANUAL:
            return
        try:
            same = self.snapshot() == self.in_file
        except ValueError:
            same = False
        if not same:
            self.notify(f'Settings modified: the configuration {self.loaded} is no longer the one of the tree')
            self.loaded = MANUAL
            self.in_file = ()
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
        if param.name() == 'type' and param.parent() is not None and param.parent().parent() is self.settings.child(
                'channels'):  # the type of a channel: its group is rebuilt
            set_type(ChannelKind.AI, param.parent(), param.value())
        if param.name() == 'type' and param.parent() is self.settings.child('trigger'):
            self.show_trigger()
        self.leave_configuration_if_modified()
        self.sync_frequencies()
        self.sync_trigger_channels()
        super().commit_settings(param)


if __name__ == '__main__':
    main(__file__, init=False)
