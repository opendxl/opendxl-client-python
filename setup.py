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
    "futures",
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

    package_data={
        "dxlclient": [
            "_vendor/msgpack/*",
            "_vendor/paho/*.*",
            "_vendor/paho/mqtt/*.*",
        ],
    },

    install_requires=[
        "asn1crypto",
        "configobj",
        "oscrypto",
        "requests"
    ],

    tests_require=[
        'futures; python_version == "2.7"',
        "mock",
        "nose",
        "parameterized",
        "requests-mock"
    ],

    extras_require={
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
        "Programming Language :: Python :: 2.7",
    ],
)
