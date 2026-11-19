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
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai1', frequency=500)
        plugin.grab_data(Naverage=10)
        assert plugin.initialized
        task = driver[-1]
        kind, name, settings = task.channels[0]
        assert (kind, name) == ('ai_voltage', 'Dev1/ai1')
        assert settings['terminal_config'] == TerminalConfiguration.DIFF
        assert (settings['min_val'], settings['max_val']) == (-10., 10.)
        name, rate, kwargs = task.timing_calls[0]
        assert rate == 500 and kwargs['samps_per_chan'] == 10
        plugin.close()

    def test_0d_is_the_mean_of_as_many_samples_as_the_averaging_of_the_viewer(self, qapp, driver):
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0')
        dte = grab_and_wait(plugin, naverage=10)
        assert driver[-1].timing_calls[0][2]['samps_per_chan'] == 10
        assert len(driver[-1].read_timeouts) == 1  # one acquisition, not ten
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

    def test_1d_averages_naverage_traces(self, qapp, driver):
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0', Nsamples=5)
        plugin.settings.child('display').setValue('1D')
        plugin.grab_data(Naverage=3)
        assert len(driver[-1].read_timeouts) == 3
        assert driver[-1].timing_calls[0][2]['samps_per_chan'] == 5
        plugin.close()

    def test_nsamples_is_only_shown_for_a_trace(self, qapp, driver):
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0')
        nsamples = plugin.settings.child('Nsamples')
        assert not nsamples.opts['visible']
        display = plugin.settings.child('display')
        display.setValue('1D')
        plugin.commit_settings(display)
        assert nsamples.opts['visible']
        plugin.close()

    def test_each_grab_stops_the_task_so_that_it_can_run_again(self, qapp, driver):
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0')
        plugin.grab_data()
        plugin.grab_data()
        assert driver[-1].stops == 2 and not driver[-1].started
        plugin.close()

    def test_changing_a_setting_replaces_the_task(self, qapp, driver):
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0', frequency=100)
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


class TestLive:
    def test_each_block_of_samples_is_emitted_as_a_data_without_further_grab_calls(self, qapp, qtbot, driver):
        from nidaqmx.constants import AcquisitionType
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0', frequency=100)
        emitted = []
        plugin.dte_signal.connect(emitted.append)

        plugin.grab_data(Naverage=10, live=True)
        live_task = driver[-1]
        assert live_task.timing_calls[0][2]['sample_mode'] == AcquisitionType.CONTINUOUS
        for _ in range(2):
            with qtbot.waitSignal(plugin.dte_signal, timeout=2000):
                live_task.fire_samples()

        assert len(emitted) == 2
        assert emitted[0][0].dim == 'Data0D'
        assert float(emitted[0][0].data[0][0]) == pytest.approx(0.45)  # the double reads s / 10 for sample s
        assert live_task.starts == 1  # one start, not one per data
        plugin.stop()
        plugin.close()

    def test_1d_live_emits_the_trace_of_each_block(self, qapp, qtbot, driver):
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0', Nsamples=10, frequency=100)
        plugin.settings.child('display').setValue('1D')
        plugin.grab_data(live=True)

        with qtbot.waitSignal(plugin.dte_signal, timeout=2000) as blocker:
            driver[-1].fire_samples()

        dte = blocker.args[0]
        assert dte[0].dim == 'Data1D' and dte[0].data[0].shape == (10,)
        assert dte[0].data[0][3] == pytest.approx(0.3)
        plugin.stop()
        plugin.close()

    def test_1d_live_emits_the_mean_of_the_last_naverage_traces(self, qapp, qtbot, driver):
        import numpy as np
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0', Nsamples=4)
        plugin.settings.child('display').setValue('1D')
        plugin.grab_data(Naverage=2, live=True)
        live_task = driver[-1]
        blocks = iter([np.full((1, 4), 1.), np.full((1, 4), 3.), np.full((1, 4), 5.)])
        live_task.read = lambda number_of_samples_per_channel=None, timeout=10.: next(blocks)[0].tolist()
        means = []
        for _ in range(3):
            with qtbot.waitSignal(plugin.dte_signal, timeout=2000) as blocker:
                live_task.fire_samples()
            means.append(float(blocker.args[0][0].data[0][0]))

        assert means == [1., 2., 4.]  # the first trace alone, then (1+3)/2, then (3+5)/2
        plugin.stop()
        plugin.close()

    def test_stopping_the_live_gives_back_the_task_of_the_snaps(self, qapp, driver):
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0')
        plugin.grab_data(live=True)
        live_task = driver[-1]

        plugin.stop()

        assert live_task.closed  # a stopped task keeps its channels reserved: it must be closed
        dte = grab_and_wait(plugin)
        assert dte[0].dim == 'Data0D'
        assert not driver[-1].closed and driver[-1] is not live_task
        plugin.close()

    def test_no_data_is_emitted_after_the_stop(self, qapp, qtbot, driver):
        plugin = make_detector(DAQ_0DViewer_DAQmxAI, ai_channel='Dev1/ai0')
        emitted = []
        plugin.dte_signal.connect(emitted.append)
        plugin.grab_data(live=True)
        live_task = driver[-1]
        live_task.fire_samples()  # queued, not yet delivered to the Qt thread

        plugin.stop()
        qtbot.wait(100)

        assert emitted == []
        plugin.close()
