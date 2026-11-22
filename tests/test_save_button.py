"""The save button of the NI viewers: a click asks for the suffix and the module, then triggers the save."""
import pytest

pytest.importorskip('nidaqmx')
pytest.importorskip('pymodaq')

from pyqtgraph.parametertree import Parameter, ParameterTree

from pymodaq_gui.parameter import pymodaq_ptypes  # noqa: F401  (registers the parameter types)

from pymodaq_plugins_daqmx.hardware.national_instruments import save_button


def make_tree(qtbot):
    group = Parameter.create(name='config', type='group', children=[save_button.save_param(suffix='lab', module='Mod1')])
    tree = ParameterTree()
    tree.setParameters(group, showTop=False)
    qtbot.addWidget(tree)
    return group, tree


def click(tree, group):
    item = next(i for i in _items(tree) if getattr(i, 'param', None) is group.child('save'))
    item.widget.button.click()


def _items(tree):
    stack = [tree.invisibleRootItem()]
    while stack:
        item = stack.pop()
        yield item
        stack.extend(item.child(i) for i in range(item.childCount()))


def test_a_click_asks_for_the_suffix_and_the_module_then_activates(qtbot, monkeypatch):
    group, tree = make_tree(qtbot)
    asked = []

    def ask(suffix, module):
        asked.append((suffix, module))
        return 'mine', 'Mod2'

    monkeypatch.setattr(save_button, 'ask_target', ask)
    activated = []
    group.child('save').sigActivated.connect(activated.append)
    click(tree, group)
    assert asked == [('lab', 'Mod1')]  # pre-filled with the options of the button
    assert (group.child('save').opts['suffix'], group.child('save').opts['module']) == ('mine', 'Mod2')
    assert len(activated) == 1


def test_cancelling_the_dialog_does_nothing(qtbot, monkeypatch):
    group, tree = make_tree(qtbot)
    monkeypatch.setattr(save_button, 'ask_target', lambda suffix, module: None)
    activated = []
    group.child('save').sigActivated.connect(activated.append)
    click(tree, group)
    assert activated == [] and (group.child('save').opts['suffix'], group.child('save').opts['module']) == ('lab', 'Mod1')
