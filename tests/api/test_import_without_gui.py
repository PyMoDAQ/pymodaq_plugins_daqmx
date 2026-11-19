"""Public API: usable without Qt nor the PyMoDAQ GUI."""
import subprocess
import sys

import pytest

pytest.importorskip('nidaqmx')


def test_importing_the_api_loads_neither_qt_nor_pymodaq():
    code = ("import sys\n"
            "import pymodaq_plugins_daqmx.hardware.national_instruments.api\n"
            "loaded = [m for m in sys.modules if m.split('.')[0] in ('pymodaq', 'pymodaq_gui', 'qtpy', "
            "'PySide6', 'PyQt5', 'PyQt6', 'PySide2')]\n"
            "assert not loaded, loaded\n")

    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
