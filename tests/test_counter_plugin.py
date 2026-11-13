"""Behaviour of the counter plugin against a fake of the NIDAQmx wrapper (no hardware, no NI driver)."""
import pytest

pytest.importorskip('nidaqmx')
pytest.importorskip('pymodaq')

from pymodaq.utils.plugin_testing import make_detector, grab_and_wait

from pymodaq_plugins_daqmx.daq_viewer_plugins.plugins_0D import daq_0Dviewer_DAQmx_Counter as module
from pymodaq_plugins_daqmx.daq_viewer_plugins.plugins_0D.daq_0Dviewer_DAQmx_Counter import DAQ_0DViewer_DAQmx_Counter

from fake_nidaqmx import FakeNIDAQmx


@pytest.fixture
def counter(qapp, monkeypatch):
    monkeypatch.setattr(module, 'NIDAQmx', FakeNIDAQmx)
    plugin = make_detector(DAQ_0DViewer_DAQmx_Counter, counter_channel='Dev1/ctr0', clock_channel='Dev1/ctr1',
                           clock_freq=100.)
    assert plugin.initialized
    yield plugin
    plugin.close()


def test_the_clock_times_the_counter(counter):
    clock, edges = counter.controller['clock'], counter.controller['counter']
    assert clock.channels[0].name == 'Dev1/ctr1' and clock.channels[0].clock_frequency == 100.
    assert edges.channels[0].name == 'Dev1/ctr0'
    name, rate, kwargs = edges.task.timing.calls[0]
    assert rate == 100. and kwargs['source'] == '/Dev1/ctr1InternalOutput'


def test_value_is_a_rate_in_counts_per_second(counter):
    dte = grab_and_wait(counter)
    dwa = dte[0]
    assert dwa.labels == ['Count rate']
    assert dwa.units == 'counts/s'
    assert float(dwa.data[0][0]) == pytest.approx(50 * 100.)  # 50 counts in 10 ms


def test_the_rate_follows_the_counting_time(counter):
    counter.settings.child('clock_freq').setValue(50.)
    assert float(grab_and_wait(counter)[0].data[0][0]) == pytest.approx(50 * 50.)


def test_each_grab_arms_the_counter_and_runs_the_clock(counter):
    grab_and_wait(counter)
    grab_and_wait(counter)
    assert counter.controller['counter'].task.started == 2
    assert counter.controller['clock'].task.started == 2
    assert not counter.controller['clock'].task.running


def test_close_releases_both_tasks(counter):
    controllers = list(counter.controller.values())
    counter.close()
    assert all(c.closed for c in controllers)
