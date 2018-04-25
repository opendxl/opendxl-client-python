# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
################################################################################

""" Global configuration functions. """

from __future__ import absolute_import
import os

if os.name.lower() == "posix":
    PATH_CACHE = "/var/McAfee/{0}".format("dxlclient")
else:
    PATH_CACHE = "./.{0}".format("dxlclient")

PATH_CONFIG = PATH_CACHE + '/conf'
PATH_KEYSTORE = PATH_CACHE + '/keystore'
PATH_LOGS = PATH_CACHE + '/logs'

FILE_CA_BUNDLE = "cabundle.pem"

FILE_CERT_PFX = "dxlcert.p12"
FILE_CERT_PEM = "dxlcert.pem"
FILE_DXL_PRIVATE_KEY = "dxlprivatekey.pem"

FILE_CONFIG = PATH_CONFIG + '/config'


def get_cache_dir():
    """
    Returns current cache folder.

    :returns: {@code string}: Cache folder.
    """
    return PATH_CACHE


def get_config_dir():
    """
    Returns current configuration folder.

    :returns: {@code string}: Configuration folder.
    """
    return PATH_CONFIG


def get_keystore_dir():
    """
    Returns current keystore folder.

    :returns: {@code string}: Keystore folder.
    """
    return PATH_KEYSTORE


def get_logs_dir():
    """
    Returns current logs folder.

    :returns: {@code string}: Logs folder.
    """
    return PATH_LOGS


def get_ca_bundle_pem():
    """
    Returns current CA Bundle filename.

    :returns: {@code string}: CA Bundle filename.
    """
    return os.path.join(PATH_KEYSTORE, FILE_CA_BUNDLE)


def get_cert_file_pfx():
    """
    Returns current PFX certificate filename.

    :returns: {@code string}: PFX certificate filename.
    """
    return os.path.join(PATH_KEYSTORE, FILE_CERT_PFX)


def get_cert_file_pem():  # pylint: disable=invalid-name
    """
    Returns current PEM certificate filename.

    :returns: {@code string}: PEM certificate filename.
    """
    return os.path.join(PATH_KEYSTORE, FILE_CERT_PEM)

def get_dxl_private_key():  # pylint: disable=invalid-name
    """
    Returns current PEM certificate filename.

    :returns: {@code string}: PEM certificate filename.
    """
    return os.path.join(PATH_KEYSTORE, FILE_DXL_PRIVATE_KEY)

def get_dxl_config_file():
    """
    Returns default dxl config file

    :return:
    """
    return FILE_CONFIG
