# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
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
        Python 3 wrapper for getting a dictionary iterator.

        :param d: The dictionary
        :return: The iterator.
        """
        return d.items()
    def is_string(obj):
        """
        Python 3 wrapper for determining if an object is a "string" (unicode).

        :param obj: The object
        :return: True if the object is a unicode string, False if not.
        :rtype: bool
        """
        return isinstance(obj, str)
else:
    def iter_dict_items(d):
        """
        Python 2 wrapper for getting a dictionary iterator.

        :param d: The dictionary
        :return: The iterator.
        """
        return d.iteritems()
    def is_string(obj):
        """
        Python 2 wrapper for determining if an object is a "string" (unicode
        or byte-string).

        :param obj: The object
        :return: True if the object is a "string", False if not.
        :rtype: bool
        """
        return isinstance(obj, basestring)
