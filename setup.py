from setuptools import setup
import distutils.command.sdist

from pkg_resources import Distribution
from distutils.dist import DistributionMetadata
import setuptools.command.sdist

# Patch setuptools' sdist behaviour with distutils' sdist behaviour
setuptools.command.sdist.sdist.run = distutils.command.sdist.sdist.run

VERSION = __import__('dxlclient').get_product_version()

dist = setup(
    # Application name:
    name="dxlclient",

    # Version number:
    version=VERSION,

    # Application author details:
    author="McAfee, Inc.",

    # License
    license="Apache License 2.0",

    keywords=['opendxl', 'dxl', 'mcafee', 'client'],

    # Packages
    packages=[
        "dxlclient",
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
