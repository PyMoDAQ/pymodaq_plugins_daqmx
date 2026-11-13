"""Behaviour of the analog input plugins against a fake of the NIDAQmx wrapper (no hardware, no NI driver)."""
import pytest

pytest.importorskip('nidaqmx')
pytest.importorskip('pymodaq')

from pymodaq.utils.plugin_testing import make_detector, grab_and_wait

from pymodaq_plugins_daqmx.hardware.national_instruments import NIDAQmx_AI
from pymodaq_plugins_daqmx.daq_viewer_plugins.plugins_0D.daq_0Dviewer_DAQmxAI import DAQ_0DViewer_DAQmxAI
from pymodaq_plugins_daqmx.daq_viewer_plugins.plugins_0D.daq_0Dviewer_DAQmxDualAI import DAQ_0DViewer_DAQmxDualAI

from fake_nidaqmx import FakeNIDAQmx


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setattr(NIDAQmx_AI, 'NIDAQmx', FakeNIDAQmx)


def make(cls, **settings):
    # the channel lists are read from the hardware at import time: with no device they are empty
    plugin = make_detector(cls, **settings)
    return plugin


class TestAI:
    def test_ini_configures_one_channel_task(self, qapp, fake):
        plugin = make(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai1', frequency=500, Nsamples=10)
        assert plugin.initialized
        assert [ch.name for ch in plugin.controller.channels] == ['Dev1/ai1']
        assert plugin.controller.clock.frequency == 500
        assert plugin.controller.clock.Nsamples == 10
        plugin.close()

    def test_0d_is_the_mean_of_the_samples(self, qapp, fake):
        plugin = make(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0', Nsamples=10)
        dte = grab_and_wait(plugin)
        assert dte[0].dim == 'Data0D'
        assert dte[0].labels == ['Dev1/ai0']
        assert float(dte[0].data[0][0]) == pytest.approx(1.)
        plugin.close()

    def test_1d_gives_the_trace_and_a_time_axis(self, qapp, fake):
        plugin = make(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0', Nsamples=10, frequency=100)
        plugin.settings.child('display').setValue('1D')
        dte = grab_and_wait(plugin)
        assert dte[0].dim == 'Data1D'
        assert dte[0].data[0].shape == (10,)
        assert dte[0].axes[0].get_data()[1] == pytest.approx(0.01)
        plugin.close()

    def test_hardware_averaging_reads_n_times(self, qapp, fake):
        plugin = make(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0', Nsamples=5)
        plugin.grab_data(Naverage=3)
        assert len(plugin.controller.reads) == 3
        plugin.close()

    def test_close_releases_the_controller(self, qapp, fake):
        plugin = make(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0')
        controller = plugin.controller
        plugin.close()
        assert controller.closed


class TestDualAI:
    def test_two_channels_two_traces(self, qapp, fake):
        plugin = make(DAQ_0DViewer_DAQmxDualAI, ai_channel0='Dev1/ai2', ai_channel1='Dev1/ai3', Nsamples=8)
        plugin.settings.child('display').setValue('1D')
        dte = grab_and_wait(plugin)
        assert dte[0].labels == ['Dev1/ai2', 'Dev1/ai3']
        assert [float(d.mean()) for d in dte[0].data] == [1., 2.]
        assert dte[0].data[0].shape == (8,)
        plugin.close()
