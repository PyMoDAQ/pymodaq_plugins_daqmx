"""The button that saves the channels of a settings tree as a module of a configuration file.

A click, in the GUI, asks for the suffix of the file (pre-filled with the option ``suffix`` of the button), keeps it
in this option, then activates the button as an ``action_led`` does: the plugin receives the
activation, and shows how it went with the LED of the button. Import this module for the parameter type ``ni_save``
to be known.
"""
from typing import Optional

from qtpy import QtWidgets

from pymodaq_gui.parameter.pymodaq_ptypes.action_led import ActionLedParameter, ActionLedParameterItem
from pymodaq_gui.parameter.pymodaq_ptypes import registerParameterType
from pymodaq_gui.utils.status_palette import Status


def save_param(suffix: str = 'default') -> dict:
    """The button, with the suffix that its dialog proposes (and returns) as an option."""
    return {'title': 'Save as...', 'name': 'save', 'type': 'ni_save', 'limits': 'status', 'value': Status.OFF,
            'suffix': suffix}


def ask_suffix(suffix: str) -> Optional[str]:
    """Ask the suffix of the file; ``None`` if the user cancels."""
    text, ok = QtWidgets.QInputDialog.getText(
        None, 'Save the channels', 'Suffix of the file (default: no suffix):', QtWidgets.QLineEdit.Normal, suffix)
    return text.strip() if ok else None


class SaveParameterItem(ActionLedParameterItem):
    """Only the item of the GUI has a button: the dialog is asked there, never in the thread of the plugin."""

    def _wire_checkable(self, button, checkable):
        button.clicked.connect(self.ask_then_activate)

    def ask_then_activate(self):
        suffix = ask_suffix(self.param.opts['suffix'])
        if suffix is None:
            return
        self.param.opts['suffix'] = suffix  # the plugin reads it in the activated button
        self.param.activate()


class SaveParameter(ActionLedParameter):
    itemClass = SaveParameterItem


registerParameterType('ni_save', SaveParameter, override=True)
