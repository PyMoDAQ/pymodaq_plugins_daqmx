"""The examples of the documentation run, against the double of the NI-DAQmx driver (no hardware needed)."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip('nidaqmx')

from nidaqmx_double import driver, system_driver  # noqa: F401  (pytest fixtures)

EXAMPLES = Path(__file__).parent.parent / 'docs' / 'source' / 'examples'


def load(name):
    spec = importlib.util.spec_from_file_location(f'example_{name}', EXAMPLES / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(name, **kwargs):
    return load(name).main(**kwargs)


def test_discover_hardware(system_driver):
    report = run('discover_hardware')
    assert set(report) == {'Dev1', 'Dev2'}
    assert report['Dev2']['analog outputs'][0] == 'Dev2/ao0'


def test_analog_input(driver):
    data = run('analog_input')
    assert data.shape == (2, 1000)
    assert driver[-1].closed and driver[-1].stops == 1


def test_analog_output(driver):
    waveform = run('analog_output')
    assert driver[0].writes == [(1.5, True)]
    assert driver[1].writes[0][0] == pytest.approx(waveform.tolist()) and not driver[1].writes[0][1]
    assert driver[1].started or driver[1].starts == 1


def test_counter_rate(driver, monkeypatch):
    from nidaqmx_double import DoubleTask
    monkeypatch.setattr(DoubleTask, 'edges_per_sample', 50)
    assert run('counter_rate', frequency=100.) == pytest.approx(5000.)
    assert all(task.closed for task in driver)


def test_triggered_acquisition(driver, system_driver):
    data = run('triggered_acquisition')
    assert data.shape == (1, 100)
    assert driver[-1].trigger_calls[0][:2] == ('dig_edge', '/Dev2/PFI0')


def test_samples_ready(driver):
    recorder = run('samples_ready')
    assert driver[-1].closed


def test_the_listener_of_the_example_is_told_by_the_driver(driver):
    example = load('samples_ready')
    config = example.TaskConfig(channels=[example.AIVoltage('Dev1/ai0')],
                                timing=example.ClockSettings(rate=1000., samples=100))
    recorder = example.Recorder()
    with example.AnalogInputTask(config) as task:
        task.add_listener(recorder)
        task.start(notify_every=10)
        driver[-1].fire_samples()
        driver[-1].fire_done(0)
    assert recorder.blocks[0].shape == (1, 10) and recorder.status == 0
