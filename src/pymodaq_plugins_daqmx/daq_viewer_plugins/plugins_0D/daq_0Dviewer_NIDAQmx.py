"""Generic viewer of the analog inputs of any NI device, on the ``nidaqmx`` API.

How this module is organised:

* helpers on terminals (``_exporting_module``, ``is_signal_terminal``) and the settings of one module (``module_group``);
* ``DAQ_0DViewer_NIDAQmx``, whose sections are, in order: configuration files (menu, load, save), the channels and
  the module groups of the tree (``sync_modules``), the start trigger of a module, what is acquired
  (``acquisitions``), and the reaction to a change of a setting (``commit_settings``).

The acquisition itself (tasks, clocks, order of start, emission of the data) is in ``DAQ_Viewer_AIBase``.
"""
import re
from typing import Dict, List, Optional

from nidaqmx.constants import Edge, Slope
from pymodaq.control_modules.thread_commands import ThreadStatus
from pymodaq.control_modules.viewer_utility_classes import main
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq_gui.utils.status_palette import Status
from pyqtgraph.parametertree import Parameter

from pymodaq_plugins_daqmx.hardware.national_instruments.NIDAQmx_AI import Acquisition, DAQ_Viewer_AIBase
from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AnalogEdgeTrigger, ChannelKind, DigitalEdgeTrigger, NIDAQSystem)
from pymodaq_plugins_daqmx.hardware.national_instruments.channel_group import channels_of, unread_of
from pymodaq_plugins_daqmx.hardware.national_instruments.channel_tree import set_type, update_suffixes
from pymodaq_plugins_daqmx.hardware.national_instruments.config_files import Configuration, ConfigFiles
from pymodaq_plugins_daqmx.hardware.national_instruments.save_button import save_param

MANUAL = '(manual)'    # no configuration file: the channels are the ones of the tree
TRIGGER_TYPES = ['none', 'digital edge', 'analog edge']  # the types of start trigger of a module
CLOCK_INTERNAL = 'internal'  # the sample clock of the module itself
DEFAULT = 'default'    # the name of the configuration of the file without suffix


# --- terminals --------------------------------------------------------------------------------------------------

def _exporting_module(terminal: str, subsystem: str = 'ai') -> Optional[str]:
    """The module that produces the signal ``terminal`` (``/Dev1/ai/SampleClock`` is produced by ``Dev1`` for the
    subsystem ``ai``), None for any other terminal (``/Dev1/PFI0``, a wire). It tells which task has to be started
    before another one."""
    parts = (terminal or '').split('/')
    return parts[1] if len(parts) > 3 and parts[0] == '' and parts[2] == subsystem else None


# what the driver lists as terminals but cannot be a clock or a trigger source
_NOT_A_SOURCE = re.compile(r'^/[^/]+/((ai|ao)\d+|ctr\d+|port\d+(/line\d+)?|APFI\d+)$', re.IGNORECASE)


def is_signal_terminal(terminal: str) -> bool:
    """Whether ``terminal`` carries a signal that can be a clock or a trigger: not a channel (``/Dev1/ai0``), nor an
    analog trigger terminal (``/Dev1/APFI0``), which has its own list."""
    return _NOT_A_SOURCE.match(terminal) is None


# --- settings of a module ---------------------------------------------------------------------------------------

# the terminals that can time a task: a wire in (PFI, RTSI, PXI), or the sample clock or the timebase of a subsystem
_CLOCK_SOURCE = re.compile(r'^/[^/]+/((PFI|RTSI|PXI_Trig)\d+(/.+)?|\w+/SampleClock(Timebase)?|\w*Timebase\w*)$', re.IGNORECASE)


def is_clock_source(terminal: str) -> bool:
    """Whether ``terminal`` can be the sample clock of a task (``/Dev1/PFI1``, ``/Dev1/ao/SampleClock``)."""
    return _CLOCK_SOURCE.match(terminal) is not None


def module_group(module: str, frequency: int, clocks: List[str], terminals: List[str], channels: List[str],
                 trigger_types: List[str] = TRIGGER_TYPES) -> dict:
    """The settings of a module: its frequency, its clock and its start trigger."""
    return {'title': module, 'name': module, 'type': 'group', 'children': [
        {'title': 'Frequency:', 'name': 'frequency', 'type': 'int', 'value': frequency, 'min': 1,
         'tip': 'Sampling rate; with an external clock, the real frequency of that clock (the highest it may have)'},
        {'title': 'Clock:', 'name': 'clock', 'type': 'list', 'limits': clocks, 'value': CLOCK_INTERNAL,
         'tip': 'The clock of the module, or a terminal (a clock wired in, or the clock that another module exports)'},
        {'title': 'Start trigger:', 'name': 'trigger', 'type': 'group', 'children': [
            {'title': 'Type:', 'name': 'type', 'type': 'list', 'limits': trigger_types, 'value': 'none'},
            {'title': 'Terminal:', 'name': 'terminal', 'type': 'list', 'limits': terminals, 'visible': False},
            {'title': 'Channel:', 'name': 'channel', 'type': 'list', 'limits': channels, 'visible': False,
             'tip': 'A channel of this module (it is acquired) or a dedicated analog trigger terminal'},
            {'title': 'Edge:', 'name': 'edge', 'type': 'list', 'limits': ['rising', 'falling'], 'value': 'rising',
             'visible': False},
            {'title': 'Level (V):', 'name': 'level', 'type': 'float', 'value': 0., 'visible': False,
             'tip': 'Inside the range of the channel'},
        ]},
    ]}


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
        {'title': 'Modules:', 'name': 'modules', 'type': 'group', 'children': []},
        {'title': 'Channels:', 'name': 'channels', 'type': 'ni_channels', 'kind': ChannelKind.AI.value,
         'limits': [], 'children': []},
    ]
    data_name = 'NI AI'
    # what distinguishes the subclasses for other inputs (the digital lines): the kind of channels of the tree (it
    # also names the subsystem of the driver that exports the clock and the trigger of a module: ``/Dev1/ai/...``),
    # the types of start trigger, and whether there are files
    kind = ChannelKind.AI
    trigger_types = TRIGGER_TYPES
    has_configuration = True

    @property
    def subsystem(self) -> str:
        """The part of the terminal names that the driver gives to the subsystem of the channels (``ai``, ``di``)."""
        return self.kind.value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        system = NIDAQSystem()
        self.settings.child('channels').setLimits(system.all_channels(self.kind))
        self.terminals = {device: system.terminals(device) for device in system.devices()}  # of each device
        self.files = ConfigFiles()
        self.loaded = MANUAL  # the configuration whose channels are in the tree
        self.in_file = ()  # what the file describes (see `snapshot`), to tell if the tree still is the file
        if self.has_configuration:
            self.refresh_menu()

    # --- configuration files: menu, load, save ------------------------------------------------------------------

    def refresh_menu(self) -> None:
        """List the files of the configuration folder in the menu, after ``(manual)``."""
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
        self.sync_modules()
        for module in self.modules():  # what the file does not give goes back to the default
            group = self.settings.child('modules', module)
            group.child('frequency').setValue(configuration.frequency(module) or self.settings['frequency'])
            group.child('clock').setValue(configuration.clock(module) or CLOCK_INTERNAL)
            self.set_module_trigger(module, configuration.trigger(module))
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
        self.sync_modules()
        channels = self.channels()
        if not channels:
            raise ValueError('There is no channel to save')
        unread = unread_of(self.settings.child('channels'))
        by_module = self.channels_by_module()
        configuration = self.files.load(suffix) if self.files.path(suffix).exists() else Configuration()
        for module in [name for name in configuration.modules if name not in by_module]:
            del configuration.modules[module]
        for module, module_channels in by_module.items():
            configuration = configuration.with_channels(
                module, module_channels, unread=[c.name for c in module_channels if c.name in unread])
            group = self.settings.child('modules', module)
            configuration = configuration.with_frequency(module, group['frequency'])
            configuration = configuration.with_clock(module, '' if group['clock'] == CLOCK_INTERNAL else group['clock'])
            configuration = configuration.with_trigger(module, self.trigger_keys(module))
        self.files.save(suffix, configuration)
        self.refresh_menu()
        self.loaded, self.in_file = _label(suffix), self.snapshot()  # the tree is that file now
        self.settings.child('config', 'configuration').setValue(self.loaded)
        self.notify(f'Channels saved in the configuration {_label(suffix)}')

    # --- feedback to the control module -------------------------------------------------------------------------

    def notify(self, message: str) -> None:
        """Tell the control module that the action succeeded: its LED is back to normal."""
        self.emit_status(ThreadCommand('Update_Status', [message, 'log']))

    def fail(self, error: Exception) -> None:
        """Tell the control module that the action failed: its LED shows the error and its message."""
        self.emit_status(ThreadCommand(ThreadStatus.ERROR, str(error)))

    # --- channels and module groups of the tree -----------------------------------------------------------------

    def channels(self) -> list:
        """The channels of the API that the tree describes, in the order of the tree."""
        return channels_of(self.settings.child('channels'))

    def channels_by_module(self) -> Dict[str, list]:
        """The channels of the tree grouped by module (the device their name starts with), in order of appearance."""
        by_module = {}
        for channel in self.channels():
            by_module.setdefault(channel.name.split('/')[0], []).append(channel)
        return by_module

    def modules(self) -> List[str]:
        """The modules of the channels of the tree (the device a channel name starts with), in order of appearance."""
        names = [child.opts['title'].split('/')[0] for child in self.settings.child('channels').children()]
        return list(dict.fromkeys(names))

    def sync_modules(self) -> None:
        """One group of settings for each module of the channels (frequency, clock, start trigger): a new module
        starts at the global frequency, on its own clock, without trigger. The lists of terminals follow the modules:
        a module can use the clock or the start trigger that another module of the tree exports."""
        group = self.settings.child('modules')
        modules = self.modules()
        for child in group.children():
            if child.name() not in modules:
                group.removeChild(child)
        for module in modules:
            lists = self.module_lists(module)
            if module not in group.names:
                group.addChild(module_group(module, self.settings['frequency'], trigger_types=self.trigger_types, **lists))
                continue
            self.set_limits(group.child(module, 'clock'), lists['clocks'])
            self.set_limits(group.child(module, 'trigger', 'terminal'), lists['terminals'])
            self.set_limits(group.child(module, 'trigger', 'channel'), lists['channels'])

    @staticmethod
    def set_limits(param: Parameter, limits: List[str]) -> None:
        """Change the limits only when they differ: setting them sends them to the GUI and resets its combo box."""
        if param.opts['limits'] != limits:
            param.setLimits(limits)

    def reachable_devices(self, module: str) -> List[str]:
        """The devices whose terminals can reach ``module``: itself and, for a module of a chassis, the chassis and the
        other modules of that chassis (a board cannot be wired to another device by software)."""
        try:
            chassis = NIDAQSystem().chassis(module)
        except ValueError:  # not a device of the system
            chassis = ''
        if not chassis:
            return [module]
        return [device for device in self.terminals
                if device in (module, chassis) or self.chassis_of(device) == chassis]

    @staticmethod
    def chassis_of(device: str) -> str:
        try:
            return NIDAQSystem().chassis(device)
        except ValueError:
            return ''

    def module_lists(self, module: str) -> dict:
        """What the settings of ``module`` choose among. A terminal of its own ``ai`` subsystem cannot time it, and
        only the devices that can reach the module offer terminals (see ``reachable_devices``)."""
        reachable = self.reachable_devices(module)
        others = [m for m in self.modules() if m != module and m in reachable]
        own = f'/{module}/{self.subsystem}/'
        terminals = [t for device in reachable for t in self.terminals.get(device, [])
                     if not t.startswith(own) and is_signal_terminal(t)]
        names = [child.opts['title'] for child in self.settings.child('channels').children()
                 if child.opts['title'].split('/')[0] == module]
        try:  # the dedicated analog trigger terminals of the device, which are not read
            apfi = [t for t in NIDAQSystem().terminals(module) if '/APFI' in t]
        except ValueError:  # a module that is not a device of the system
            apfi = []
        # the clock sources of all the devices, and the sample clock that another module of the tree exports
        clocks = ([CLOCK_INTERNAL] + [t for t in terminals if is_clock_source(t)]
                  + [f'/{m}/{self.subsystem}/SampleClock' for m in others])
        starts = terminals + [f'/{m}/{self.subsystem}/StartTrigger' for m in others]
        return {'clocks': list(dict.fromkeys(clocks)), 'terminals': list(dict.fromkeys(starts)),
                'channels': names + apfi}

    # --- start trigger of a module ------------------------------------------------------------------------------

    def module_trigger(self, module: str):
        """The start trigger of ``module`` as the API describes it, None if it starts at once."""
        keys = self.trigger_keys(module)
        if keys is None:
            return None
        if keys['type'] == 'digital edge':
            return DigitalEdgeTrigger(keys['terminal'], Edge[keys['edge'].upper()])
        return AnalogEdgeTrigger(keys['channel'], keys['level'], Slope[keys['edge'].upper()])

    def trigger_keys(self, module: str) -> Optional[dict]:
        """The start trigger of ``module`` as the keys of the ``trigger`` table of a file, or None."""
        settings = self.settings.child('modules', module, 'trigger')
        if settings['type'] == 'digital edge':
            return {'type': 'digital edge', 'terminal': settings['terminal'], 'edge': settings['edge']}
        if settings['type'] == 'analog edge':
            return {'type': 'analog edge', 'channel': settings['channel'], 'level': settings['level'],
                    'edge': settings['edge']}
        return None

    def set_module_trigger(self, module: str, keys: Optional[dict]) -> None:
        """Put the trigger of a file in the tree (no trigger if the file has none)."""
        settings = self.settings.child('modules', module, 'trigger')
        keys = keys or {'type': 'none'}
        settings.child('type').setValue(keys['type'])
        for key in ('terminal', 'channel', 'level'):
            if key in keys:
                settings.child(key).setValue(keys[key])
        settings.child('edge').setValue(keys.get('edge', 'rising'))
        self.show_trigger(module)

    def show_trigger(self, module: str) -> None:
        """Only the parameters of the chosen type of trigger are visible."""
        settings = self.settings.child('modules', module, 'trigger')
        kind = settings['type']
        settings.child('terminal').setOpts(visible=kind == 'digital edge')
        settings.child('channel').setOpts(visible=kind == 'analog edge')
        settings.child('level').setOpts(visible=kind == 'analog edge')
        settings.child('edge').setOpts(visible=kind != 'none')

    # --- what is acquired ---------------------------------------------------------------------------------------

    def acquisitions(self) -> List[Acquisition]:
        """One task for each module: its channels are acquired together, at its frequency, on its clock, started by
        its trigger.

        ``waits_for`` lists the other modules whose exported signal (clock or start trigger) this module uses: the
        base class starts those that wait first and the provider last."""
        self.sync_modules()  # the channels may have been added without the GUI telling the plugin
        by_module = self.channels_by_module()
        unread = unread_of(self.settings.child('channels'))
        acquisitions = []
        for module, channels in by_module.items():
            group = self.settings.child('modules', module)
            clock = '' if group['clock'] == CLOCK_INTERNAL else group['clock']  # '' = the module's own clock
            trigger = self.module_trigger(module)
            # the parameter of the trigger that names its source depends on the type of trigger
            key = {'digital edge': 'terminal', 'analog edge': 'channel'}.get(group['trigger', 'type'])
            sources = [clock] + ([group['trigger', key]] if key is not None else [])
            waits = tuple(dict.fromkeys(m for m in (_exporting_module(source, self.subsystem) for source in sources)
                                        if m not in (None, module) and m in by_module))
            acquisitions.append(Acquisition(module, channels, group['frequency'],
                                            tuple(c.name for c in channels if c.name in unread), clock, trigger, waits))
        return acquisitions

    def snapshot(self) -> tuple:
        """What a configuration file describes in the tree: the channels and, for each module, its frequency, clock
        and trigger."""
        self.sync_modules()
        modules = tuple((module, self.settings['modules', module, 'frequency'],
                         self.settings['modules', module, 'clock'], self.trigger_keys(module))
                        for module in self.modules())
        return tuple(self.channels()), tuple(unread_of(self.settings.child('channels'))), modules

    def leave_configuration_if_modified(self) -> None:
        """The menu goes back to ``(manual)`` as soon as the tree is not what the file describes any more: its
        channels, the frequency, clock or trigger of a module (a value that cannot be a channel is a modification
        too). The menu thus never shows a configuration that is not in the tree, and choosing the file again reloads
        it."""
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

    # --- reaction to a change of a setting ----------------------------------------------------------------------

    def commit_settings(self, param: Parameter) -> None:
        """What the plugin does when a setting changed (in the GUI or by code).

        The first branch handles the configuration actions (load, save); then the rebuilding of the tree that a
        parameter requires (a type of channel, the units of a range, a type of trigger). Any change finally checks
        that the tree still is the loaded configuration and updates the groups of the modules.
        """
        button = param  # the one of the GUI: it holds what its dialog returned
        param = self.own(param)
        parent = param.parent()
        in_a_channel = parent is not None and parent.parent() is self.settings.child('channels')
        if self.has_configuration and param.name() == 'configuration' and parent is self.settings.child('config'):
            self.load_configuration()
        elif self.has_configuration and param.opts['type'] == 'ni_save':  # the button has been clicked, after the dialog of the GUI
            param.opts.update(suffix=button.opts['suffix'])
            try:
                self.save_configuration(param)
                param.setValue(Status.IDLE)
            except (ValueError, OSError) as error:
                param.setValue(Status.ERROR)
                self.fail(error)
        if param.name() == 'type' and in_a_channel:  # the type of a channel: its group is rebuilt
            set_type(self.kind, parent, param.value())
        if param.name() == 'units' and in_a_channel:  # the units of a temperature: the range follows
            update_suffixes(parent)
        if param.name() == 'type' and parent is not None and parent.name() == 'trigger':
            self.show_trigger(parent.parent().name())  # only the parameters of that type of trigger are visible
        self.leave_configuration_if_modified()
        self.sync_modules()
        super().commit_settings(param)


if __name__ == '__main__':
    main(__file__, init=False)
