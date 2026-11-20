"""The Qt bridge turns the notifications of a task (raised on driver threads) into Qt signals on the Qt thread.

Tested through its public signals only, with the NI-DAQmx driver replaced by a double that calls back from a
thread of its own, as the real driver does.
"""
import threading

import numpy as np
import pytest

pytest.importorskip('nidaqmx')
pytest.importorskip('qtpy')

from pymodaq_plugins_daqmx.hardware.national_instruments.api import (
    AIVoltage, AnalogInputTask, ClockSettings, TaskConfig)
from pymodaq_plugins_daqmx.hardware.national_instruments.qt_task_bridge import QtTaskBridge

from nidaqmx_double import driver  # noqa: F401  (pytest fixture)


def make_task():
    return AnalogInputTask(TaskConfig((AIVoltage('Dev1/ai0', -10, 10),), timing=ClockSettings(rate=100, samples=4)))


def test_blocks_of_samples_arrive_as_a_signal_on_the_qt_thread(qapp, qtbot, driver):
    bridge = QtTaskBridge(make_task())
    received = []
    bridge.samples_ready.connect(lambda data: received.append((data, threading.current_thread())))
    bridge.start(notify_every=2)

    with qtbot.waitSignal(bridge.samples_ready, timeout=2000):
        driver[-1].fire_samples()

    data, thread = received[0]
    assert driver[-1].callback_threads == ['driver']  # the driver did call back from its own thread
    assert thread is threading.main_thread()
    assert isinstance(data, np.ndarray) and data.shape == (1, 2)


def test_the_end_of_the_task_arrives_as_a_signal_with_its_status_on_the_qt_thread(qapp, qtbot, driver):
    bridge = QtTaskBridge(make_task())
    received = []
    bridge.done.connect(lambda status: received.append((status, threading.current_thread())))
    bridge.start()

    with qtbot.waitSignal(bridge.done, timeout=2000) as blocker:
        driver[-1].fire_done(-200284)

    assert blocker.args == [-200284]
    assert received == [(-200284, threading.main_thread())]


def test_a_closed_bridge_emits_nothing_more(qapp, qtbot, driver):
    bridge = QtTaskBridge(make_task())
    received = []
    bridge.samples_ready.connect(received.append)
    bridge.done.connect(received.append)
    bridge.start(notify_every=2)

    bridge.close()  # to be called before closing the task: the task must not keep a reference to the bridge
    driver[-1].fire_samples()
    driver[-1].fire_done(0)
    qtbot.wait(100)

    assert received == []
