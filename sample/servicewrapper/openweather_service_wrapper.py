# This sample demonstrates wrapping an existing service and exposing it on the
# DXL fabric.
#
# In this particular case, the "openweathermap.org" current weather data is
# exposed as a DXL service. This service wrapper delegates to the
# OpenWeatherMap REST API.
#
# openweather_common.py must be edited to include the OpenWeatherMap API
# key (see http://openweathermap.org/appid)

import logging
import os
import sys
import time
import urllib2

from dxlclient.callbacks import RequestCallback
from dxlclient.client import DxlClient
from dxlclient.client_config import DxlClientConfig
from dxlclient.message import ErrorResponse, Response
from dxlclient.service import ServiceRegistrationInfo

from openweather_common import *

# Import common logging and configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from common import *

# Configure local logger
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# The OpenWeatherMap "Current Weather" URL (see http://openweathermap.org/current)
CURRENT_WEATHER_URL = "http://api.openweathermap.org/data/2.5/weather?{0}&APPID={1}"

# Create DXL configuration from file
config = DxlClientConfig.create_dxl_config_from_file(CONFIG_FILE)

# Create the client
with DxlClient(config) as client:

    # Connect to the fabric
    client.connect()

    #
    # Register the service
    #

    # Create "Current Weather" incoming request callback
    class CurrentWeatherCallback(RequestCallback):
        def on_request(self, request):
            try:
                # Extract information from request
                query = request.payload.decode(encoding="UTF-8")
                logger.info("Service received request payload: " + query)

                # Send HTTP request to OpenWeatherMap
                req = urllib2.Request(
                    CURRENT_WEATHER_URL.format(query, API_KEY), None,
                    {'Content-Type': 'text/json'})
                f = urllib2.urlopen(req)
                weather_response = f.read()
                f.close()

                # Create the response message
                response = Response(request)
                # Populate the response payload
                response.payload = weather_response.encode(encoding="UTF-8")
                # Send the response
                client.send_response(response)

            except Exception as ex:
                print str(ex)
                # Send error response
                client.send_response(ErrorResponse(request, error_message=str(ex).encode(encoding="UTF-8")))

    # Create service registration object
    info = ServiceRegistrationInfo(client, SERVICE_NAME)

    # Add a topic for the service to respond to
    info.add_topic(SERVICE_CURRENT_WEATHER_TOPIC, CurrentWeatherCallback())

    # Register the service with the fabric (wait up to 10 seconds for registration to complete)
    client.register_service_sync(info, 10)

    logger.info("Weather service is running...")

    # Wait forever
    while True:
        time.sleep(60)
