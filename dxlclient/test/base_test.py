""" Base class and functions for the various client tests. """

from __future__ import absolute_import
from functools import wraps
import os
import sys
try:
    # Python 3
    from urllib import request as urllib_dot_request
    from urllib import parse as urllib_dot_parse
except ImportError:
    # Python 2
    import urllib as urllib_dot_request
    import urlparse as urllib_dot_parse

from unittest import TestCase
from dxlclient import DxlClientConfig, DxlClient

# pylint: disable=missing-docstring, no-self-use


def atomize(lock):
    def decorator(wrapped):
        @wraps(wrapped)
        def _wrapper(*args, **kwargs):
            with lock:
                return wrapped(*args, **kwargs)
        return _wrapper
    return decorator


class TestDxlClient(DxlClient):
    def _destroy(self, wait_complete=True):
        client = self._client
        super(TestDxlClient, self)._destroy(wait_complete)
        if client:
            # Close out sockets that the MQTT client is holding in order to
            # avoid socket ResourceWarning messages appearing when tests are
            # run on Python 3. This should be removed when this issue is
            # addressed:
            # https://github.com/eclipse/paho.mqtt.python/issues/170
            if hasattr(client, "_sockpairR") and client._sockpairR:
                client._sockpairR.close()
                client._sockpairR = None
            if hasattr(client, "_sockpairW") and client._sockpairW:
                client._sockpairW.close()
                client._sockpairW = None


class BaseClientTest(TestCase):
    DEFAULT_TIMEOUT = 5 * 60
    DEFAULT_RETRIES = 3
    POST_OP_DELAY = 8
    REG_DELAY = 60

    def create_client(self, max_retries=DEFAULT_RETRIES, incoming_message_thread_pool_size=1):
        config = DxlClientConfig.create_dxl_config_from_file(os.path.dirname(os.path.abspath(__file__)) +
                                                             "/client_config.cfg")
        config.incoming_message_thread_pool_size = incoming_message_thread_pool_size

        config.connect_retries = max_retries

        # Check if proxy is set through environment variables
        # While running travis build, ignore proxy set through env variable
        for proxy in urllib_dot_request.getproxies().values():
            parts = urllib_dot_parse.urlparse(proxy)
            os.environ['NO_PROXY'] = parts.hostname
        return TestDxlClient(config)

if sys.version_info[0] > 2:
    import builtins # pylint: disable=import-error, unused-import
else:
    import __builtin__ # pylint: disable=import-error
    builtins = __builtin__ # pylint: disable=invalid-name
