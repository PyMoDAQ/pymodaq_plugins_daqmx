"""Relevé du comportement réel de nidaqmx sur un appareil simulé NI MAX.

Usage (Windows, driver NI-DAQmx + appareil simulé créé dans NI MAX) :
    pip install nidaqmx
    python contract_check.py [NomAppareil]      # ex. Dev1 ; défaut = premier appareil

Écrit contract_report_<appareil>.json à côté du script. Rien d'autre n'est modifié.
Chaque observation est isolée : une erreur ne bloque pas les suivantes.
"""
import json
import sys
import threading
import traceback
from pathlib import Path

import nidaqmx
import numpy as np
from nidaqmx.constants import (AcquisitionType, CurrentUnits, Edge, RTDType, TemperatureUnits,
                               TerminalConfiguration, ThermocoupleType, ResistanceConfiguration,
                               ExcitationSource)
from nidaqmx.system import System

report = {"nidaqmx_version": getattr(nidaqmx, "__version__", "?"), "python": sys.version}


def observe(name):
    def deco(fn):
        try:
            report[name] = fn()
        except Exception as e:  # on relève aussi les erreurs : ce sont des données
            report[name] = {"exception": type(e).__mro__[0].__name__,
                            "bases": [c.__name__ for c in type(e).__mro__[1:4]],
                            "message": str(e)[:300],
                            "error_code": getattr(e, "error_code", None)}
        return fn
    return deco


system = System.local()
devices = list(system.devices.device_names)
report["devices"] = devices
dev = sys.argv[1] if len(sys.argv) > 1 else (devices[0] if devices else None)
report["device_used"] = dev
if dev is None:
    sys.exit("Aucun appareil trouvé : crée un appareil simulé dans NI MAX.")
d = system.devices[dev]


def safe(fn):
    try:
        v = fn()
        return v if v is None or isinstance(v, (int, float, str, bool, dict)) else list(v)
    except Exception as e:
        return {"exception": type(e).__name__, "error_code": getattr(e, "error_code", None),
                "message": str(e)[:200]}


def rngs(flat):
    flat = list(map(float, flat))
    return [flat[i:i + 2] for i in range(0, len(flat), 2)]


# one entry per property: a property the device does not support must not hide the others
report["system_info"] = {
    "product_type": safe(lambda: d.product_type),
    "is_simulated": safe(lambda: d.is_simulated),
    "ai_physical_chans": safe(lambda: d.ai_physical_chans.channel_names),
    "ao_physical_chans": safe(lambda: d.ao_physical_chans.channel_names),
    "ci_physical_chans": safe(lambda: d.ci_physical_chans.channel_names),
    "co_physical_chans": safe(lambda: d.co_physical_chans.channel_names),
    "di_lines": safe(lambda: list(d.di_lines.channel_names)[:4]),
    "do_lines": safe(lambda: list(d.do_lines.channel_names)[:4]),
    "terminals_sample": safe(lambda: list(d.terminals)[:6]),
    "ai_voltage_rngs": safe(lambda: rngs(d.ai_voltage_rngs)),
    "ao_voltage_rngs": safe(lambda: rngs(d.ao_voltage_rngs)),
    "ai_current_rngs": safe(lambda: rngs(d.ai_current_rngs)),
    "ai_max_multi_chan_rate": safe(lambda: d.ai_max_multi_chan_rate),
    "ai_max_single_chan_rate": safe(lambda: d.ai_max_single_chan_rate),
    "ao_max_rate": safe(lambda: d.ao_max_rate),
    "ai_trig_usage": safe(lambda: [str(x) for x in d.ai_trig_usage]),
    "di_trig_usage": safe(lambda: [str(x) for x in d.di_trig_usage]),
}


def shape_of(x):
    a = np.asarray(x)
    return {"type": type(x).__name__, "shape": list(a.shape), "dtype": str(a.dtype),
            "first": a.ravel()[:3].tolist()}


@observe("ai_channel_kinds_probe")
def _():
    """For C series modules: which kind of AI channel the first channel accepts, and what a read gives."""
    chans = list(d.ai_physical_chans.channel_names)
    if not chans:
        return "no AI channel on this device (for a chassis, run the script on a module, e.g. cDAQ1Mod1)"
    ch = chans[0]
    kinds = {
        "voltage": lambda t: t.ai_channels.add_ai_voltage_chan(ch),
        "current": lambda t: t.ai_channels.add_ai_current_chan(ch, units=CurrentUnits.AMPS),
        "thermocouple": lambda t: t.ai_channels.add_ai_thrmcpl_chan(
            ch, thermocouple_type=ThermocoupleType.K, units=TemperatureUnits.DEG_C),
        "rtd": lambda t: t.ai_channels.add_ai_rtd_chan(
            ch, rtd_type=RTDType.PT_3851, resistance_config=ResistanceConfiguration.THREE_WIRE,
            current_excit_source=ExcitationSource.INTERNAL, current_excit_val=0.001),
    }
    out = {"channel": ch, "product_type": safe(lambda: d.product_type)}
    for name, add in kinds.items():
        try:
            with nidaqmx.Task() as t:
                add(t)
                out[name] = shape_of(t.read())
        except Exception as e:
            out[name] = {"exception": type(e).__name__, "error_code": getattr(e, "error_code", None),
                         "message": str(e)[:200]}
    return out


@observe("read_one_channel_finite_N_samples")
def _():
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0")
        t.timing.cfg_samp_clk_timing(1000.0, sample_mode=AcquisitionType.FINITE, samps_per_chan=10)
        return shape_of(t.read(number_of_samples_per_channel=10))


@observe("read_one_channel_single_sample")
def _():
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0")
        return shape_of(t.read())


@observe("read_two_channels_finite_N_samples")
def _():
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0:1")
        t.timing.cfg_samp_clk_timing(1000.0, sample_mode=AcquisitionType.FINITE, samps_per_chan=10)
        return shape_of(t.read(number_of_samples_per_channel=10))


@observe("read_two_channels_single_sample")
def _():
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0:1")
        return shape_of(t.read())


@observe("read_two_channels_all_available_default")
def _():
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0:1")
        t.timing.cfg_samp_clk_timing(1000.0, sample_mode=AcquisitionType.FINITE, samps_per_chan=5)
        t.start()
        t.wait_until_done(timeout=5)
        return shape_of(t.read(number_of_samples_per_channel=nidaqmx.constants.READ_ALL_AVAILABLE))


@observe("read_timeout_error")
def _():
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0")
        t.timing.cfg_samp_clk_timing(1.0, sample_mode=AcquisitionType.FINITE, samps_per_chan=100)
        return t.read(number_of_samples_per_channel=100, timeout=0.2)


@observe("unknown_device_error")
def _():
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan("NoSuchDev/ai0")


@observe("unknown_channel_error")
def _():
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(f"{dev}/ai9999")


@observe("invalid_range_error")
def _():
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0", min_val=-1000.0, max_val=1000.0)


@observe("invalid_rate_error")
def _():
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0")
        t.timing.cfg_samp_clk_timing(1e12, sample_mode=AcquisitionType.FINITE, samps_per_chan=10)
        t.start()


@observe("bad_trigger_source_error")
def _():
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0")
        t.timing.cfg_samp_clk_timing(1000.0, sample_mode=AcquisitionType.FINITE, samps_per_chan=10)
        t.triggers.start_trigger.cfg_dig_edge_start_trig("/NoSuchDev/PFI0", Edge.RISING)
        t.start()


@observe("callbacks_finite_task")
def _():
    events = {"samples": [], "done": []}
    got_done = threading.Event()
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0")
        t.timing.cfg_samp_clk_timing(1000.0, sample_mode=AcquisitionType.FINITE, samps_per_chan=100)

        def on_samples(task_handle, event_type, n, cb_data):
            events["samples"].append({"thread": threading.current_thread().name, "n": n,
                                      "event_type": str(event_type), "cb_data": cb_data})
            task.read(number_of_samples_per_channel=n)
            return 0

        def on_done(task_handle, status, cb_data):
            events["done"].append({"thread": threading.current_thread().name, "status": status})
            got_done.set()
            return 0

        task = t
        t.register_every_n_samples_acquired_into_buffer_event(50, on_samples)
        t.register_done_event(on_done)
        t.start()
        got_done.wait(5)
        events["done_received"] = got_done.is_set()
        events["main_thread"] = threading.current_thread().name
        return events


@observe("start_stop_restart")
def _():
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0")
        t.timing.cfg_samp_clk_timing(1000.0, sample_mode=AcquisitionType.FINITE, samps_per_chan=10)
        out = {}
        t.start(); t.wait_until_done(5); t.stop()
        out["is_task_done_after_stop"] = t.is_task_done()
        t.start(); t.wait_until_done(5); t.stop()
        out["second_start_ok"] = True
        t.start()
        try:
            t.start()
        except Exception as e:
            out["double_start"] = {"exception": type(e).__name__, "code": getattr(e, "error_code", None)}
        return out


@observe("close_then_use_error")
def _():
    t = nidaqmx.Task()
    t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0")
    t.close()
    return t.read()


@observe("write_scalar_and_array_ao")
def _():
    out = {}
    with nidaqmx.Task() as t:
        t.ao_channels.add_ao_voltage_chan(f"{dev}/ao0")
        out["scalar_return"] = t.write(0.5, auto_start=True)
        t.stop()
    with nidaqmx.Task() as t:
        t.ao_channels.add_ao_voltage_chan(f"{dev}/ao0:1")
        t.timing.cfg_samp_clk_timing(1000.0, sample_mode=AcquisitionType.FINITE, samps_per_chan=4)
        out["2d_array_return"] = t.write(np.zeros((2, 4)), auto_start=False)
    with nidaqmx.Task() as t:
        t.ao_channels.add_ao_voltage_chan(f"{dev}/ao0")
        t.timing.cfg_samp_clk_timing(1000.0, sample_mode=AcquisitionType.FINITE, samps_per_chan=4)
        out["1d_list_return"] = t.write([0.0, 0.1, 0.2, 0.3], auto_start=False)
    return out


@observe("write_wrong_shape_error")
def _():
    with nidaqmx.Task() as t:
        t.ao_channels.add_ao_voltage_chan(f"{dev}/ao0:1")
        t.write([0.1, 0.2, 0.3], auto_start=False)


@observe("counter_input_read")
def _():
    ctrs = list(d.ci_physical_chans.channel_names)
    if not ctrs:
        return "pas de compteur sur cet appareil"
    with nidaqmx.Task() as t:
        t.ci_channels.add_ci_count_edges_chan(ctrs[0])
        t.start()
        return shape_of(t.read())


@observe("digital_read_write")
def _():
    out = {}
    lines = list(d.di_lines.channel_names)
    olines = list(d.do_lines.channel_names)
    if lines:
        with nidaqmx.Task() as t:
            t.di_channels.add_di_chan(lines[0])
            out["di_single"] = shape_of(t.read())
    if olines:
        with nidaqmx.Task() as t:
            t.do_channels.add_do_chan(olines[0])
            out["do_write_return"] = t.write(True)
    return out


@observe("unsupported_terminal_config_rse")
def _():
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0", terminal_config=TerminalConfiguration.RSE)
        return shape_of(t.read(number_of_samples_per_channel=3))


def first(names):
    names = list(names)
    return names[0] if names else None


@observe("read_explicit_one_sample_shapes")
def _():
    """Shape of read(number_of_samples_per_channel=1): list or scalar, one or two channels."""
    out = {}
    for n in (1, 2):
        with nidaqmx.Task() as t:
            t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0:{n - 1}")
            t.timing.cfg_samp_clk_timing(1000.0, sample_mode=AcquisitionType.FINITE, samps_per_chan=5)
            out[f"{n}_channel"] = shape_of(t.read(number_of_samples_per_channel=1))
    return out


@observe("external_sample_clock_source")
def _():
    pfi = first(t_ for t_ in d.terminals if "PFI" in t_)
    if pfi is None:
        return "no PFI terminal"
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0")
        t.timing.cfg_samp_clk_timing(1000.0, source=pfi, active_edge=Edge.RISING,
                                     sample_mode=AcquisitionType.FINITE, samps_per_chan=5)
        t.start()
        return {"source": pfi, "started": True}


@observe("digital_edge_start_trigger_valid_source")
def _():
    pfi = first(t_ for t_ in d.terminals if "PFI" in t_)
    if pfi is None:
        return "no PFI terminal"
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0")
        t.timing.cfg_samp_clk_timing(1000.0, sample_mode=AcquisitionType.FINITE, samps_per_chan=5)
        t.triggers.start_trigger.cfg_dig_edge_start_trig(pfi, Edge.RISING)
        t.start()
        return {"source": pfi, "started": True}


@observe("analog_edge_start_trigger")
def _():
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0")
        t.timing.cfg_samp_clk_timing(1000.0, sample_mode=AcquisitionType.FINITE, samps_per_chan=5)
        t.triggers.start_trigger.cfg_anlg_edge_start_trig(f"{dev}/ai0", trigger_level=1.0)
        t.start()
        return {"started": True}


@observe("change_detection_timing_digital_input")
def _():
    line = first(d.di_lines.channel_names)
    if line is None:
        return "no digital input line"
    with nidaqmx.Task() as t:
        t.di_channels.add_di_chan(line)
        t.timing.cfg_change_detection_timing(rising_edge_chan=line, falling_edge_chan=line,
                                             sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=10)
        t.start()
        return {"line": line, "started": True}


@observe("counter_output_pulse_frequency")
def _():
    ctr = first(c for c in d.co_physical_chans.channel_names if "ctr" in c)
    if ctr is None:
        return "no counter output"
    with nidaqmx.Task() as t:
        t.co_channels.add_co_pulse_chan_freq(ctr, freq=1000.0, duty_cycle=0.5)
        t.timing.cfg_implicit_timing(sample_mode=AcquisitionType.CONTINUOUS)
        t.start()
        running = not t.is_task_done()
        t.stop()
        return {"counter": ctr, "running_after_start": running}


@observe("counter_input_count_edges_with_clock")
def _():
    ctr = first(d.ci_physical_chans.channel_names)
    pfi = first(t_ for t_ in d.terminals if "PFI" in t_)
    if ctr is None or pfi is None:
        return "no counter input or no PFI terminal"
    with nidaqmx.Task() as t:
        t.ci_channels.add_ci_count_edges_chan(ctr)
        t.timing.cfg_samp_clk_timing(1000.0, source=pfi, sample_mode=AcquisitionType.FINITE, samps_per_chan=5)
        t.start()
        return shape_of(t.read(number_of_samples_per_channel=1, timeout=0.5))


def _write_one_channel(data):
    with nidaqmx.Task() as t:
        t.ao_channels.add_ao_voltage_chan(f"{dev}/ao0")
        t.timing.cfg_samp_clk_timing(1000.0, sample_mode=AcquisitionType.FINITE, samps_per_chan=4)
        return t.write(data, auto_start=False)


# one observation per shape: the first one to fail must not hide the others
@observe("ao_one_channel_write_python_list")
def _():
    return _write_one_channel([0.0, 0.1, 0.2, 0.3])


@observe("ao_one_channel_write_numpy_1d")
def _():
    return _write_one_channel(np.zeros(4))


@observe("ao_one_channel_write_numpy_2d_1xN")
def _():
    return _write_one_channel(np.zeros((1, 4)))


@observe("ao_one_channel_write_numpy_2d_Nx1_transposed")
def _():
    return _write_one_channel(np.zeros((4, 1)))


@observe("digital_write_several_lines")
def _():
    """write() on a task holding several digital output lines: accepted value shapes."""
    lines = list(d.do_lines.channel_names)
    if len(lines) < 2:
        return "fewer than two digital output lines"
    out = {}
    for label, data in (("list_of_bool", [True, False]), ("list_of_list", [[True], [False]]),
                        ("ndarray_bool", np.array([True, False])), ("scalar", True)):
        try:
            with nidaqmx.Task() as t:
                t.do_channels.add_do_chan(f"{lines[0]}:{lines[1].split('/')[-1]}")
                out[label] = t.write(data, auto_start=True)
        except Exception as e:
            out[label] = {"exception": type(e).__name__, "error_code": getattr(e, "error_code", None),
                          "message": str(e)[:200]}
    return out


@observe("digital_read_several_lines")
def _():
    lines = list(d.di_lines.channel_names)
    if len(lines) < 2:
        return "fewer than two digital input lines"
    with nidaqmx.Task() as t:
        t.di_channels.add_di_chan(f"{lines[0]}:{lines[1].split('/')[-1]}")
        return shape_of(t.read())


@observe("counter_input_read_without_clock")
def _():
    """read() on a counter task with no sample clock: single sample and N samples."""
    ctr = first(d.ci_physical_chans.channel_names)
    if ctr is None:
        return "no counter input"
    out = {}
    for label, kwargs in (("default", {}), ("one_sample", {"number_of_samples_per_channel": 1}),
                          ("five_samples", {"number_of_samples_per_channel": 5})):
        try:
            with nidaqmx.Task() as t:
                t.ci_channels.add_ci_count_edges_chan(ctr)
                t.start()
                out[label] = shape_of(t.read(timeout=0.5, **kwargs))
        except Exception as e:
            out[label] = {"exception": type(e).__name__, "error_code": getattr(e, "error_code", None),
                          "message": str(e)[:200]}
    return out


def _callbacks_observation(add_channel, configure_timing):
    """Register sample and done callbacks on a task, run it, report thread names and counts."""
    seen = {"samples": [], "done": []}

    def on_samples(task_handle, event_type, n, cb_data):
        seen["samples"].append({"thread": threading.current_thread().name, "n": n})
        return 0

    def on_done(task_handle, status, cb_data):
        seen["done"].append({"thread": threading.current_thread().name, "status": status})
        return 0

    done = threading.Event()
    with nidaqmx.Task() as t:
        add_channel(t)
        configure_timing(t)
        try:
            t.register_every_n_samples_acquired_into_buffer_event(5, on_samples)
        except Exception as e:
            seen["register_samples_error"] = {"exception": type(e).__name__,
                                              "error_code": getattr(e, "error_code", None)}
        t.register_done_event(lambda h, s, c: (on_done(h, s, c), done.set(), 0)[-1])
        t.start()
        seen["done_received"] = done.wait(2.0)
    seen["main_thread"] = threading.current_thread().name
    return seen


@observe("callbacks_counter_input_task")
def _():
    ctr = first(d.ci_physical_chans.channel_names)
    pfi = first(t_ for t_ in d.terminals if "PFI" in t_)
    if ctr is None or pfi is None:
        return "no counter input or no PFI terminal"
    return _callbacks_observation(
        lambda t: t.ci_channels.add_ci_count_edges_chan(ctr),
        lambda t: t.timing.cfg_samp_clk_timing(1000.0, source=pfi, sample_mode=AcquisitionType.FINITE,
                                               samps_per_chan=10))


@observe("callbacks_digital_input_task")
def _():
    line = first(d.di_lines.channel_names)
    if line is None:
        return "no digital input line"
    return _callbacks_observation(
        lambda t: t.di_channels.add_di_chan(line),
        lambda t: t.timing.cfg_samp_clk_timing(1000.0, sample_mode=AcquisitionType.FINITE, samps_per_chan=10))


@observe("callbacks_counter_output_task")
def _():
    ctr = first(c for c in d.co_physical_chans.channel_names if "ctr" in c)
    if ctr is None:
        return "no counter output"
    seen = {"done": []}
    done = threading.Event()

    def on_done(h, s, c):
        seen["done"].append({"thread": threading.current_thread().name, "status": s})
        done.set()
        return 0

    with nidaqmx.Task() as t:
        t.co_channels.add_co_pulse_chan_freq(ctr, freq=1000.0, duty_cycle=0.5)
        t.timing.cfg_implicit_timing(sample_mode=AcquisitionType.FINITE, samps_per_chan=10)
        t.register_done_event(on_done)
        t.start()
        seen["done_received"] = done.wait(2.0)
    return seen


@observe("digital_edge_start_trigger_on_digital_line")
def _():
    """Is a digital line (not a PFI terminal) accepted as the source of a digital edge start trigger?"""
    line = first(d.di_lines.channel_names)
    if line is None:
        return "no digital input line"
    out = {}
    for label, source in (("line_name", line), ("terminal_name", "/" + line)):
        try:
            with nidaqmx.Task() as t:
                t.ai_channels.add_ai_voltage_chan(f"{dev}/ai0")
                t.timing.cfg_samp_clk_timing(1000.0, sample_mode=AcquisitionType.FINITE, samps_per_chan=5)
                t.triggers.start_trigger.cfg_dig_edge_start_trig(source, Edge.RISING)
                t.start()
                out[label] = {"source": source, "started": True}
        except Exception as e:
            out[label] = {"source": source, "exception": type(e).__name__,
                          "error_code": getattr(e, "error_code", None), "message": str(e)[:200]}
    return out


out = Path(__file__).with_name(f"contract_report_{dev}.json")
out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
print(f"OK -> {out}")
for k, v in report.items():
    flag = "EXC" if isinstance(v, dict) and "exception" in v else "ok "
    print(f"[{flag}] {k}")
