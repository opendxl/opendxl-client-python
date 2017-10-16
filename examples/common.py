"""
Common definitions for the DXL Python SDK samples.

This includes the defining the path to the configuration file used to initialize the DXL client
in addition to setting up the logger appropriately.
"""

import os
import logging

# Config file name.
CONFIG_FILE_NAME = "dxlclient.config"
CONFIG_FILE = os.path.dirname(os.path.abspath(__file__)) + "/" + CONFIG_FILE_NAME

# Enable logging, this will also direct built-in DXL log messages.
# See - https://docs.python.org/2/howto/logging-cookbook.html
log_formatter = logging.Formatter('%(asctime)s %(name)s - %(levelname)s - %(message)s')

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)
