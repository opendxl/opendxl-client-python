""" Setup script for the dxlclient package """

# pylint: disable=no-member, no-name-in-module, import-error, wrong-import-order
# pylint: disable=missing-docstring, no-self-use

from __future__ import absolute_import
import glob
import os
from setuptools import Command, setup
import setuptools.command.sdist
import distutils.command.sdist
import distutils.log
import subprocess


# Patch setuptools' sdist behaviour with distutils' sdist behaviour
setuptools.command.sdist.sdist.run = distutils.command.sdist.sdist.run

PRODUCT_PROPS = {}
CWD = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(CWD, "dxlclient", "_product_props.py")) as f:
    exec(f.read(), PRODUCT_PROPS) # pylint: disable=exec-used

class LintCommand(Command):
    """
    Custom setuptools command for running lint
    """
    description = 'run lint against project source files'
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        self.announce("Running pylint for library source files and tests",
                      level=distutils.log.INFO)
        subprocess.check_call(["pylint", "dxlclient"] + glob.glob("*.py"))
        self.announce("Running pylint for examples", level=distutils.log.INFO)
        subprocess.check_call(["pylint"] + glob.glob("examples/*.py") +
                              glob.glob("examples/**/*.py") +
                              ["--rcfile", ".pylintrc.examples"])

class CiCommand(Command):
    """
    Custom setuptools command for running steps that are performed during
    Continuous Integration testing.
    """
    description = 'run CI steps (lint, test, etc.)'
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        self.run_command("lint")
        self.run_command("test")

TEST_REQUIREMENTS = [
    'futures; python_version == "2.7"',
    "mock",
    "nose",
    "parameterized",
    "pylint",
    "requests-mock"
]

DEV_REQUIREMENTS = TEST_REQUIREMENTS + ["sphinx"]

setup(
    # Application name:
    name="dxlclient",

    # Version number:
    version=PRODUCT_PROPS["__version__"],

    # Application author details:
    author="McAfee, Inc.",

    # License
    license="Apache License 2.0",

    keywords=['opendxl', 'dxl', 'mcafee', 'client'],

    # Custom Paho MQTT Python client with proxy support added as a git submodule
    package_dir={'pahoproxy': 'paho_mqtt_dxl/src/paho/mqtt'},

    # Packages
    packages=[
        "dxlclient",
        "dxlclient._cli",
        "pahoproxy"
    ],

    # Include additional files into the package
    include_package_data=True,

    install_requires=[
        "asn1crypto",
        "configobj",
        "msgpack>=0.5",
        "oscrypto",
        "requests",
        "PySocks<1.7"
    ],

    tests_require=TEST_REQUIREMENTS,

    extras_require={
        "dev": DEV_REQUIREMENTS,
        "test": TEST_REQUIREMENTS
    },

    test_suite="nose.collector",

    # Details
    url="http://www.mcafee.com/",

    description="McAfee Data Exchange Layer Client",

    long_description=open('README').read(),

    python_requires='>=2.7.9,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*',

    classifiers=[
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7"
    ],

    cmdclass={
        'ci': CiCommand,
        'lint': LintCommand
    },

    entry_points={
        'console_scripts': [
            'dxlclient = dxlclient._cli:cli_run'
        ],
    }
)
