"""The button that saves the channels of a settings tree as a module of a configuration file.

A click, in the GUI, asks for the suffix of the file and the name of the module (pre-filled with the ones of the group
of the button), puts them in the group, then activates the button as an ``action_led`` does: the plugin receives the
activation, and shows how it went with the LED of the button. Import this module for the parameter type ``ni_save``
to be known.
"""
from typing import List, Optional, Tuple

from qtpy import QtWidgets

from pymodaq_gui.parameter.pymodaq_ptypes.action_led import ActionLedParameter, ActionLedParameterItem
from pymodaq_gui.parameter.pymodaq_ptypes import registerParameterType
from pymodaq_gui.utils.status_palette import Status


def save_params(suffix: str = 'default', module: str = '') -> List[dict]:
    """The children of the ``save`` group: the two values of the dialog (kept in the group, so that the plugin finds
    them) and the button."""
    return [{'title': 'Suffix:', 'name': 'suffix', 'type': 'str', 'value': suffix, 'visible': False},
            {'title': 'Module:', 'name': 'module', 'type': 'str', 'value': module, 'visible': False},
            {'title': 'Save as...', 'name': 'save', 'type': 'ni_save', 'limits': 'status', 'value': Status.IDLE}]


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
        group = self.param.parent()
        target = ask_target(group['suffix'], group['module'])
        if target is None:
            return
        group.child('suffix').setValue(target[0])
        group.child('module').setValue(target[1])
        self.param.activate()


class SaveParameter(ActionLedParameter):
    itemClass = SaveParameterItem


registerParameterType('ni_save', SaveParameter, override=True)
