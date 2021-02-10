from setuptools import setup, find_packages
import toml

config = toml.load('./plugin_info.toml')
PLUGIN_NAME = f"pymodaq_plugins_{config['plugin-info']['SHORT_PLUGIN_NAME']}"


from pathlib import Path

with open(str(Path(__file__).parent.joinpath(f'src/{PLUGIN_NAME}/VERSION')), 'r') as fvers:
    version = fvers.read().strip()


with open('README.rst') as fd:
    long_description = fd.read()

setupOpts = dict(
    name=PLUGIN_NAME,
    description=description,
    long_description=long_description,
    license='CECILL B',
    url=package_url,
    author=author,
    author_email=author_email,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Development Status :: 5 - Production/Stable",
        "Environment :: Other Environment",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Human Machine Interfaces",
        "Topic :: Scientific/Engineering :: Visualization",
        "License :: CeCILL-B Free Software License Agreement (CECILL-B)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: User Interfaces",
    ], )


setup(
    version=version,
    packages=find_packages(where='./src'),
    package_data={'': ['*.dll']},
    include_package_data=True,
    entry_points={'pymodaq.plugins': f'{SHORT_PLUGIN_NAME} = {PLUGIN_NAME}'},
    install_requires=['toml', ]+config['plugin-install']['packages-required'],
    **setupOpts
)

