# This sample demonstrates wrapping an existing service and exposing it on the
# DXL fabric.
#
# In this particular case, the "openweathermap.org" current weather data is
# exposed as a DXL service. This service wrapper delegates to the
# OpenWeatherMap REST API.
#
# openweather_common.py must be edited to include the OpenWeatherMap API
# key (see http://openweathermap.org/appid)

import json
import logging
import os
import sys

from dxlclient.client import DxlClient
from dxlclient.client_config import DxlClientConfig
from dxlclient.message import Message, Request

from openweather_common import *

# Import common logging and configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from common import *

# Configure local logger
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Create DXL configuration from file
config = DxlClientConfig.create_dxl_config_from_file(CONFIG_FILE)

# Create the client
with DxlClient(config) as client:

    # Connect to the fabric
    client.connect()

    #
    # Invoke the service (send a request)
    #

    # Create the "Current Weather" request
    req = Request(SERVICE_CURRENT_WEATHER_TOPIC)
    # Populate the request payload
    # Examples include:
    #   By ZIP code: zip=97140,us
    #   By geographic coordinates: lat=35&lon=139
    #   By city name: q=London,uk
    req.payload = "zip=97140,us".encode()

    # Send the request and wait for a response (synchronous)
    res = client.sync_request(req)

    # Extract information from the response (if an error did not occur)
    if res.message_type != Message.MESSAGE_TYPE_ERROR:
        response_dict = json.loads(res.payload.decode(encoding="UTF-8"))
        print "Client received response payload: \n" + \
          json.dumps(response_dict, sort_keys=True, indent=4, separators=(',', ': '))
    else:
        logger.error("Error: " + res.error_message + " (" + str(res.error_code) + ")")