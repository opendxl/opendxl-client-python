# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2018 McAfee Inc. - All Rights Reserved.
################################################################################

""" Abstraction layer for Python 2 / 3 compatibility. """

import sys

# pylint: disable=invalid-name, unused-import, undefined-variable

try:
    from queue import Queue
except ImportError:
    from Queue import Queue

if sys.version_info[0] > 2:
    def iter_dict_items(d):
        """
        Python 3 wrapper for getting a version-compatible dictionary iterator.

        :param d: The dictionary
        :return: The iterator.
        """
        return d.items()
    string = str
else:
    def iter_dict_items(d):
        """
        Python 2 wrapper for getting a version-compatible dictionary iterator.

        :param d: The dictionary
        :return: The iterator.
        """
        return d.iteritems()
    string = basestring
