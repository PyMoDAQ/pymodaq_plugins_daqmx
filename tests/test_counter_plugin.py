"""Behaviour of the counter plugin, with the NI-DAQmx driver replaced by a double (no hardware needed)."""
import pytest

pytest.importorskip('nidaqmx')
pytest.importorskip('pymodaq')

from nidaqmx.constants import AcquisitionType
from pymodaq.utils.plugin_testing import make_detector, grab_and_wait

from pymodaq_plugins_daqmx.daq_viewer_plugins.plugins_0D.daq_0Dviewer_DAQmx_Counter import DAQ_0DViewer_DAQmx_Counter

from nidaqmx_double import driver, DoubleTask  # noqa: F401  (pytest fixture)


@pytest.fixture
def counter(qapp, driver, monkeypatch):
    monkeypatch.setattr(DoubleTask, 'edges_per_sample', 50)  # 50 edges while the clock ticks once
    plugin = make_detector(DAQ_0DViewer_DAQmx_Counter, counter_channel='Dev2/ctr0', clock_channel='Dev2/ctr1',
                           clock_freq=100.)
    assert plugin.initialized
    yield plugin
    plugin.close()


def clock_task(driver):
    return next(t for t in driver if t.channels and t.channels[0][0] == 'co_pulse_freq')


def edges_task(driver):
    return next(t for t in driver if t.channels and t.channels[0][0] == 'ci_count_edges')


def test_the_clock_times_the_counter(counter, driver):
    kind, name, settings = clock_task(driver).channels[0]
    assert name == 'Dev2/ctr1' and settings['freq'] == 100.
    kind, name, settings = edges_task(driver).channels[0]
    assert name == 'Dev2/ctr0'
    name, rate, kwargs = edges_task(driver).timing_calls[0]
    assert rate == 100. and kwargs['source'] == '/Dev2/Ctr1InternalOutput'
    assert kwargs['sample_mode'] == AcquisitionType.FINITE and kwargs['samps_per_chan'] == 1


def test_value_is_a_rate_in_counts_per_second(counter):
    dte = grab_and_wait(counter)
    dwa = dte[0]
    assert dwa.labels == ['Count rate']
    assert dwa.units == 'counts/s'
    assert float(dwa.data[0][0]) == pytest.approx(50 * 100.)  # 50 counts in 10 ms


def test_the_rate_follows_the_counting_time(counter):
    param = counter.settings.child('clock_freq')
    param.setValue(50.)
    counter.commit_settings(param)
    assert float(grab_and_wait(counter)[0].data[0][0]) == pytest.approx(50 * 50.)


def test_each_grab_arms_the_counter_and_runs_the_clock(counter, driver):
    grab_and_wait(counter)
    grab_and_wait(counter)
    assert edges_task(driver).starts == 2
    assert clock_task(driver).starts == 2
    assert not clock_task(driver).started


def test_close_releases_both_tasks(counter, driver):
    counter.close()
    assert clock_task(driver).closed and edges_task(driver).closed
