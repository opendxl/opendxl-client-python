from functools import wraps
from unittest import TestCase
from dxlclient import DxlClientConfig, DxlClient
import os


def atomize(lock):
    def decorator(wrapped):
        @wraps(wrapped)
        def _wrapper(*args, **kwargs):
            with lock:
                return wrapped(*args, **kwargs)
        return _wrapper
    return decorator


class BaseClientTest(TestCase):
    DEFAULT_TIMEOUT = 5 * 60
    DEFAULT_RETRIES = 3
    POST_OP_DELAY = 8
    REG_DELAY = 60

    def create_client(self, max_retries=DEFAULT_RETRIES, incoming_message_thread_pool_size = 1):
        config = DxlClientConfig.create_dxl_config_from_file(os.path.dirname(os.path.abspath(__file__)) +
                                                              "/client_config.cfg")
        config.incoming_message_thread_pool_size = incoming_message_thread_pool_size

        config.connect_retries = max_retries
        return DxlClient(config)
