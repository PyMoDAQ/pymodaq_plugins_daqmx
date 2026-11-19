"""Behaviour of the analog input plugins, with the NI-DAQmx driver replaced by a double (no hardware needed)."""
import pytest

pytest.importorskip('nidaqmx')
pytest.importorskip('pymodaq')

from nidaqmx.constants import TerminalConfiguration
from pymodaq.utils.plugin_testing import make_detector, grab_and_wait

from pymodaq_plugins_daqmx.daq_viewer_plugins.plugins_0D.daq_0Dviewer_DAQmxAI import DAQ_0DViewer_DAQmxAI
from pymodaq_plugins_daqmx.daq_viewer_plugins.plugins_0D.daq_0Dviewer_DAQmxDualAI import DAQ_0DViewer_DAQmxDualAI

from nidaqmx_double import driver  # noqa: F401  (pytest fixture)


class TestAI:
    def test_ini_configures_one_channel_task(self, qapp, driver):
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai1', frequency=500, Nsamples=10)
        assert plugin.initialized
        task = driver[-1]
        kind, name, settings = task.channels[0]
        assert (kind, name) == ('ai_voltage', 'Dev1/ai1')
        assert settings['terminal_config'] == TerminalConfiguration.DIFF
        assert (settings['min_val'], settings['max_val']) == (-10., 10.)
        name, rate, kwargs = task.timing_calls[0]
        assert rate == 500 and kwargs['samps_per_chan'] == 10
        plugin.close()

    def test_0d_is_the_mean_of_the_samples(self, qapp, driver):
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0', Nsamples=10)
        dte = grab_and_wait(plugin)
        assert dte[0].dim == 'Data0D'
        assert dte[0].labels == ['Dev1/ai0']
        assert float(dte[0].data[0][0]) == pytest.approx(0.45)  # the double reads s / 10 for sample s
        plugin.close()

    def test_1d_gives_the_trace_and_a_time_axis(self, qapp, driver):
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0', Nsamples=10, frequency=100)
        plugin.settings.child('display').setValue('1D')
        dte = grab_and_wait(plugin)
        assert dte[0].dim == 'Data1D'
        assert dte[0].data[0].shape == (10,)
        assert dte[0].data[0][3] == pytest.approx(0.3)
        assert dte[0].axes[0].get_data()[1] == pytest.approx(0.01)
        plugin.close()

    def test_hardware_averaging_reads_n_times(self, qapp, driver):
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0', Nsamples=5)
        plugin.grab_data(Naverage=3)
        assert len(driver[-1].read_timeouts) == 3
        plugin.close()

    def test_each_grab_stops_the_task_so_that_it_can_run_again(self, qapp, driver):
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0', Nsamples=5)
        plugin.grab_data()
        plugin.grab_data()
        assert driver[-1].stops == 2 and not driver[-1].started
        plugin.close()

    def test_changing_a_setting_replaces_the_task(self, qapp, driver):
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0', Nsamples=5, frequency=100)
        param = plugin.settings.child('frequency')
        param.setValue(200)
        plugin.commit_settings(param)  # what the Dashboard does when the user edits a setting
        assert driver[0].closed
        assert driver[-1].timing_calls[0][1] == 200
        plugin.close()

    def test_close_releases_the_task(self, qapp, driver):
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0')
        plugin.close()
        assert driver[-1].closed


class TestDualAI:
    def test_two_channels_two_traces(self, qapp, driver):
        plugin = make_detector(DAQ_0DViewer_DAQmxDualAI, ai_channel0='Dev1/ai2', ai_channel1='Dev1/ai3', Nsamples=8)
        plugin.settings.child('display').setValue('1D')
        dte = grab_and_wait(plugin)
        assert dte[0].labels == ['Dev1/ai2', 'Dev1/ai3']
        assert [float(d.mean()) for d in dte[0].data] == pytest.approx([0.35, 1.35])  # channel c, sample s: c + s/10
        assert dte[0].data[0].shape == (8,)
        plugin.close()


@pytest.mark.parametrize('plugin_class', [DAQ_0DViewer_DAQmxAI, DAQ_0DViewer_DAQmxDualAI])
def test_live_grab_is_repeated_by_the_viewer(plugin_class):
    # a plugin that claims a live mode must keep emitting by itself after one grab_data call; these plugins
    # make one acquisition per call, so the viewer has to call them again for each data
    assert plugin_class.live_mode_available is False
