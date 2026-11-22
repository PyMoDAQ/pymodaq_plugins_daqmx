"""The save button of the NI viewers: a click asks for the suffix, then triggers the save."""
import pytest

pytest.importorskip('nidaqmx')
pytest.importorskip('pymodaq')

from pyqtgraph.parametertree import Parameter, ParameterTree

from pymodaq_gui.parameter import pymodaq_ptypes  # noqa: F401  (registers the parameter types)

from pymodaq_plugins_daqmx.hardware.national_instruments import save_button


def make_tree(qtbot):
    group = Parameter.create(name='config', type='group', children=[save_button.save_param(suffix='lab')])
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


def test_a_click_asks_for_the_suffix_then_activates(qtbot, monkeypatch):
    group, tree = make_tree(qtbot)
    asked = []

    def ask(suffix):
        asked.append(suffix)
        return 'mine'

    monkeypatch.setattr(save_button, 'ask_suffix', ask)
    activated = []
    group.child('save').sigActivated.connect(activated.append)
    click(tree, group)
    assert asked == ['lab']  # pre-filled with the option of the button
    assert group.child('save').opts['suffix'] == 'mine'
    assert len(activated) == 1


def test_cancelling_the_dialog_does_nothing(qtbot, monkeypatch):
    group, tree = make_tree(qtbot)
    monkeypatch.setattr(save_button, 'ask_suffix', lambda suffix: None)
    activated = []
    group.child('save').sigActivated.connect(activated.append)
    click(tree, group)
    assert activated == [] and group.child('save').opts['suffix'] == 'lab'
