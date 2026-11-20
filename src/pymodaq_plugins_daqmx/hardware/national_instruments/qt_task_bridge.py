"""Qt adapter of the tasks of the API: the notifications of the driver, as Qt signals on the thread of the bridge."""
from typing import Optional

import numpy as np
from qtpy import QtCore

from .api import TaskListener
from .api.tasks import _Task


class QtTaskBridge(QtCore.QObject, TaskListener):
    """Wraps a task of the API and re-emits what the driver notifies, on the thread of the bridge.

    The driver calls back from threads of its own, one per call and in no particular order. Qt widgets and the
    PyMoDAQ plugin machinery must only be touched from the thread they live in (the plugin thread for a plugin):
    connect to the signals of this bridge, not to the task.

    The bridge is a *relay* between two threads, and the thread affinity of a QObject is what makes it work:

    * the bridge lives in the thread that created it, which must run an event loop: create it where its receivers
      live, for a plugin in the plugin methods (``ini_detector``, ``grab_data``...);
    * the methods ``on_samples_ready`` and ``on_done`` are called by the driver, in the driver threads. They
      do nothing but emit private signals, whose connection is *queued*: the event is posted in the event
      queue of the bridge's thread, not handled in the driver thread;
    * the private slots then run in the bridge's thread, in the order of the queue, and emit the public signals
      there: whatever is connected to ``samples_ready`` and ``done`` is called in that thread, so it needs no lock.

    Call ``close()`` before closing the task: it stops the relay and drops what is still queued.
    """
    samples_ready = QtCore.Signal(object)  # np.ndarray shaped (channels, samples)

    done = QtCore.Signal(int)  # status of the task: 0 on success, else a driver error code

    _samples_from_driver = QtCore.Signal(object)
    _done_from_driver = QtCore.Signal(int)

    def __init__(self, task: _Task, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.task = task
        self._closed = False
        # queued: whatever thread emits the private signals, the public ones are emitted from the bridge's thread
        self._samples_from_driver.connect(self._relay_samples, QtCore.Qt.QueuedConnection)
        self._done_from_driver.connect(self._relay_done, QtCore.Qt.QueuedConnection)
        task.add_listener(self)

    # called from the driver threads (TaskListener): only hand the event over to the thread of the bridge
    def on_samples_ready(self, data: np.ndarray) -> None:
        self._samples_from_driver.emit(data)

    def on_done(self, status: int) -> None:
        self._done_from_driver.emit(status)

    # slots of the bridge itself (not the ``emit`` of a signal): Qt drops the calls queued for a bridge that is gone
    @QtCore.Slot(object)
    def _relay_samples(self, data: np.ndarray) -> None:
        if not self._closed:
            self.samples_ready.emit(data)

    @QtCore.Slot(int)
    def _relay_done(self, status: int) -> None:
        if not self._closed:
            self.done.emit(status)

    def close(self) -> None:
        """Stop listening to the task, and forget the events not yet delivered. The task itself is not closed."""
        self.task.remove_listener(self)
        self._closed = True

    def start(self, notify_every: Optional[int] = None) -> None:
        self.task.start(notify_every=notify_every)
