# This sample demonstrates how to register a DXL service to receive Request
# messages and send Response messages back to an invoking client.

import logging
import os
import sys

from dxlclient.callbacks import RequestCallback
from dxlclient.client import DxlClient
from dxlclient.client_config import DxlClientConfig
from dxlclient.message import Message, Request, Response
from dxlclient.service import ServiceRegistrationInfo

# Import common logging and configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from common import *

# Configure local logger
logging.getLogger().setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# The topic for the service to respond to
SERVICE_TOPIC = "/isecg/sample/basicservice"

# Create DXL configuration from file
config = DxlClientConfig.create_dxl_config_from_file(CONFIG_FILE)

# Create the client
with DxlClient(config) as client:

    # Connect to the fabric
    client.connect()

    #
    # Register the service
    #

    # Create incoming request callback
    class MyRequestCallback(RequestCallback):
        def on_request(self, request):
            # Extract information from request
            print "Service received request payload: " + request.payload.decode()
            # Create the response message
            res = Response(request)
            # Populate the response payload
            res.payload = "pong".encode()
            # Send the response
            client.send_response(res)

    # Create service registration object
    info = ServiceRegistrationInfo(client, "myService")

    # Add a topic for the service to respond to
    info.add_topic(SERVICE_TOPIC, MyRequestCallback())

    # Register the service with the fabric (wait up to 10 seconds for registration to complete)
    client.register_service_sync(info, 10)

    #
    # Invoke the service (send a request)
    #

    # Create the request message
    req = Request(SERVICE_TOPIC)

    # Populate the request payload
    req.payload = "ping".encode()

    # Send the request and wait for a response (synchronous)
    res = client.sync_request(req)

    # Extract information from the response (if an error did not occur)
    if res.message_type != Message.MESSAGE_TYPE_ERROR:
        print "Client received response payload: " + res.payload.decode()