# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2017 McAfee Inc. - All Rights Reserved.
################################################################################

# In order to bundle our own version of some libraries, we use the _vendor
# folder as an immutable source of external dependencies
import os
import sys
import logging
from threading import RLock

# Insert _vendor folder as the first folder when looking a library
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '_vendor'))

from dxlclient._global_settings import *
from dxlclient._product_props import *

__version__ = get_product_version()

class _NullHandler(logging.Handler):
    def emit(self, record):
        pass

logging.getLogger(__name__).addHandler(_NullHandler())

class _ObjectTracker(object):
    """
    Utility class used to track DXL Client-specific object instances
    """

    # The object tracker instance (singleton)
    _instance = None

    def __init__(self):
        """Constructor"""
        self._obj_count = 0
        self._enabled = False
        self._lock = RLock()
        self._logger = logging.getLogger(__name__)

    @property
    def enabled(self):
        """
        Whether the object tracker is enabled
        """
        return self._enabled

    @enabled.setter
    def enabled(self, val):
        self._enabled = val

    def obj_constructed(self, object):
        """
        Tracks that the specified object was constructed

        :param object: The object that was constructed
        """
        if self._enabled:
            with self._lock:
                self._obj_count += 1
                self._logger.debug("Constructed: " + object.__module__ + "." + object.__class__.__name__ \
                      + " objCount=" + str(self._obj_count))

    def obj_destructed(self, object):
        """
        Tracks that the specified object was destructed

        :param object: The object that was destructed
        """
        if self._enabled:
            with self._lock:
                self._obj_count -= 1
                self._logger.debug("Destructed: " + object.__module__ + "." + object.__class__.__name__ \
                    + " objCount=" + str(self._obj_count))

    @property
    def obj_count(self):
        """
        The current count of object instances
        """
        with self._lock:
            return self._obj_count

    @staticmethod
    def get_instance():
        """
        Returns the object tracker instance

        :return: The object tracker instance
        """
        # Instance creation should be synchronized
        if not _ObjectTracker._instance:
            _ObjectTracker._instance = _ObjectTracker()

        return _ObjectTracker._instance


class _BaseObject(object):
    """
    Base class for the DXL client-related classes
    """

    def __init__(self):
        """Constructor"""
        _ObjectTracker.get_instance().obj_constructed(self)

    def __del__(self):
        """Destructor"""
        _ObjectTracker.get_instance().obj_destructed(self)

# make all classes accessible from dxlclient package
from dxlclient._uuid_generator import *
from dxlclient.broker import *
from dxlclient._request_manager import *
from dxlclient.message import *

from dxlclient.exceptions import *
from dxlclient.callbacks import *
from dxlclient._callback_manager import *

from dxlclient.client_config import *
from dxlclient.client import *
from dxlclient._dxl_utils import *
from dxlclient.service import *


