"""The button that saves the channels of a settings tree as a module of a configuration file.

A click, in the GUI, asks for the suffix of the file and the name of the module (pre-filled with the options
``suffix`` and ``module`` of the button), keeps them in these options, then activates the button as an ``action_led`` does: the plugin receives the
activation, and shows how it went with the LED of the button. Import this module for the parameter type ``ni_save``
to be known.
"""
from typing import Optional, Tuple

from qtpy import QtWidgets

from pymodaq_gui.parameter.pymodaq_ptypes.action_led import ActionLedParameter, ActionLedParameterItem
from pymodaq_gui.parameter.pymodaq_ptypes import registerParameterType
from pymodaq_gui.utils.status_palette import Status


def save_param(suffix: str = 'default', module: str = '') -> dict:
    """The button, with the suffix and the module that its dialog proposes (and returns) as options."""
    return {'title': 'Save as...', 'name': 'save', 'type': 'ni_save', 'limits': 'status', 'value': Status.OFF,
            'suffix': suffix, 'module': module}


def ask_target(suffix: str, module: str) -> Optional[Tuple[str, str]]:
    """Ask the suffix of the file and the name of the module; ``None`` if the user cancels."""
    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle('Save the channels')
    form = QtWidgets.QFormLayout(dialog)
    suffix_edit, module_edit = QtWidgets.QLineEdit(suffix), QtWidgets.QLineEdit(module)
    form.addRow('Suffix of the file (default: no suffix):', suffix_edit)
    form.addRow('Module:', module_edit)
    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    if dialog.exec() != QtWidgets.QDialog.Accepted:
        return None
    return suffix_edit.text().strip(), module_edit.text().strip()


class SaveParameterItem(ActionLedParameterItem):
    """Only the item of the GUI has a button: the dialog is asked there, never in the thread of the plugin."""

    def _wire_checkable(self, button, checkable):
        button.clicked.connect(self.ask_then_activate)

    def ask_then_activate(self):
        target = ask_target(self.param.opts['suffix'], self.param.opts['module'])
        if target is None:
            return
        self.param.opts['suffix'], self.param.opts['module'] = target  # the plugin reads them in the activated button
        self.param.activate()


class SaveParameter(ActionLedParameter):
    itemClass = SaveParameterItem


registerParameterType('ni_save', SaveParameter, override=True)
