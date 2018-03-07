from __future__ import absolute_import
import os
from setuptools import setup
import distutils.command.sdist

from pkg_resources import Distribution
from distutils.dist import DistributionMetadata
import setuptools.command.sdist

# Patch setuptools' sdist behaviour with distutils' sdist behaviour
setuptools.command.sdist.sdist.run = distutils.command.sdist.sdist.run

product_props = {}
cwd=os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(cwd, "dxlclient", "_product_props.py")) as f:
    exec(f.read(), product_props)

TEST_REQUIREMENTS = [
    'futures; python_version == "2.7"',
    "mock",
    "nose",
    "parameterized",
    "requests-mock"
]

dist = setup(
    # Application name:
    name="dxlclient",

    # Version number:
    version=product_props["__version__"],

    # Application author details:
    author="McAfee, Inc.",

    # License
    license="Apache License 2.0",

    keywords=['opendxl', 'dxl', 'mcafee', 'client'],

    # Packages
    packages=[
        "dxlclient",
        "dxlclient._cli"
    ],

    # Include additional files into the package
    include_package_data=True,

    install_requires=[
        "asn1crypto",
        "configobj",
        "msgpack",
        "oscrypto",
        "paho-mqtt",
        "requests"
    ],

    setup_requires=[
        "nose>=1.0"
    ],

    tests_require=TEST_REQUIREMENTS,

    extras_require={
        "dev": [
            "pylint",
            "sphinx"
        ],
        "test": TEST_REQUIREMENTS
    },

    test_suite="nose.collector",

    # Details
    url="http://www.mcafee.com/",

    description="McAfee Data Exchange Layer Client",

    long_description=open('README').read(),

    classifiers=[
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6"
    ],
)
