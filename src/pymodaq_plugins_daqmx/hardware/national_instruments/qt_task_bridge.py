"""Qt adapter of the tasks of the API: the notifications of the driver, as Qt signals on the Qt thread."""
from typing import Optional

import numpy as np
from qtpy import QtCore


class QtTaskBridge(QtCore.QObject):
    """Wraps a task of the API and re-emits what the driver notifies, on the thread of the bridge.

    The driver calls back from threads of its own. Qt widgets and the PyMoDAQ plugin machinery must only be
    touched from the Qt thread: connect to the signals of this bridge instead of overriding the hooks of the task.
    Create the bridge in the Qt (main) thread.
    """
    samples_ready = QtCore.Signal(object)  # np.ndarray shaped (channels, samples)

    done = QtCore.Signal(int)  # status of the task: 0 on success, else a driver error code

    _samples_from_driver = QtCore.Signal(object)
    _done_from_driver = QtCore.Signal(int)

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        # queued: whatever thread emits the private signals, the public ones are emitted from the bridge's thread
        self._samples_from_driver.connect(self._relay_samples, QtCore.Qt.QueuedConnection)
        self._done_from_driver.connect(self._relay_done, QtCore.Qt.QueuedConnection)
        task.on_samples_ready = self._samples_from_driver.emit
        task.on_done = self._done_from_driver.emit

    # slots of the bridge itself (not the ``emit`` of a signal): Qt drops the calls queued for a bridge that is gone
    @QtCore.Slot(object)
    def _relay_samples(self, data):
        self.samples_ready.emit(data)

    @QtCore.Slot(int)
    def _relay_done(self, status):
        self.done.emit(status)

    def start(self, notify_every: Optional[int] = None):
        self.task.start(notify_every=notify_every)
