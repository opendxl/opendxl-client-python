# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
################################################################################

""" Product properties, used for packaging. """

__version__ = "5.0.0.568"

__product_id__ = "DXL_____1000"

__product_name__ = "McAfee Data Exchange Layer"

__product_props__ = {
    "General":
        {
            "Version": __version__,
            "ProductName": __product_name__,
            "Language": "0000"
        }
}

def get_product_id():
    """
    Returns DXL Client product ID.

    :returns: {@code string}: Product ID.
    """
    return __product_id__


def get_product_version():
    """
    Returns DXL Client version.

    :returns: {@code string}: version.
    """
    return __version__


def get_product_name():
    """
    Returns DXL Client product name.

    :returns: {@code string}: product name.
    """
    return __product_name__


def get_product_props():
    """
    Returns DXL Client properties.

    :returns: {@code dict}: Properties of the client..
    """
    return __product_props__
