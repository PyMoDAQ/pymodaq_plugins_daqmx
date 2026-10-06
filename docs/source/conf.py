# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import os
import sys
sys.path.insert(0, os.path.abspath('./'))
sys.path.insert(0, os.path.abspath('../'))
sys.path.insert(0, os.path.abspath('../src'))
sys.path.insert(0, os.path.abspath('../src/pymodaq_plugins_daqmx'))
sys.path.insert(0, os.path.abspath('../src/pymodaq_plugins_daqmx/hardware'))
sys.path.insert(0, os.path.abspath('../src/pymodaq_plugins_daqmx/hardware/national_instruments'))
sys.path.insert(0, os.path.abspath('../src/pymodaq_plugins_daqmx/daq_move_plugins'))
sys.path.insert(0, os.path.abspath('../src/pymodaq_plugins_daqmx/daq_viewer_plugins'))
sys.path.insert(0, os.path.abspath('../src/pymodaq_plugins_daqmx/daq_viewer_plugins/plugins_0D'))
sys.path.insert(0, os.path.abspath('../src/pymodaq_plugins_daqmx/daq_viewer_plugins/plugins_1D'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'pymodaq_plugins_daqmx'
copyright = '2025, Sébastien Weber, Aurore Finco, Sébastien Guerrero'
author = 'Sébastien Weber, Aurore Finco, Sébastien Guerrero'
release = '1.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx_rtd_theme',
              "sphinx.ext.autodoc",
              "sphinx.ext.viewcode",
              "sphinx.ext.graphviz",
              "sphinx.ext.inheritance_diagram"
              ]

autodoc_default_flags = ['members', 'inherited-members', 'show-inheritance']
autodoc_default_options = {
    "members": True,
    "special-members": "__init__",
    "inherited-members": False,
    "show-inheritance": False,
}
inheritance_graph_attrs = dict(rankdir="TB", size='""')
graphviz_dot = "C:/Program Files (x86)/Graphviz/bin/dot.exe"
templates_path = ['_templates']
exclude_patterns = ['_build']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_logo = 'images/splash.png'