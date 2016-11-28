import logging
import os
import sys

from dxlclient.callbacks import RequestCallback
from dxlclient.client import DxlClient
from dxlclient.client_config import DxlClientConfig
from dxlclient.message import Response
from dxlclient.service import ServiceRegistrationInfo

# Import common logging and configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from common import *

# Configure local logger
logger = logging.getLogger(__name__)

# Sample topic to fire Requests on
SERVICE_TOPIC = "/isecg/sample/service"

# Sample Service Provider
try:
    # Create DxlClientConfig from expected sample configuration file
    logger.info("Service Provider - Load DXL config from: %s", CONFIG_FILE)
    config = DxlClientConfig.create_dxl_config_from_file(CONFIG_FILE)

    # Initialize DXL client using our configuration
    logger.info("Service Provider - Creating DXL Client")
    with DxlClient(config) as client:

        # Connect to DXL Broker
        logger.info("Service Provider - Connecting to Broker")
        client.connect()

        # Response callback class to handle DXL Responses to our Asynchronous Requests
        class MyRequestCallback(RequestCallback):
            def on_request(self, request):
                # Extract information from Response payload, in this sample we expect it is UTF-8 encoded
                logger.info("Service Provider - Request received:\n   Topic: %s\n   Request ID: %s\n   Payload: %s",
                            request.destination_topic,
                            request.message_id,
                            request.payload.decode())

                # Create the Response message
                logger.info("Service Provider - Creating Response for Request ID %s on %s",
                            request.message_id, request.destination_topic)
                response = Response(request)

                # Encode string payload as UTF-8
                response.payload = "Sample Response Payload".encode()

                # Send the Response back
                logger.info("Service Provider - Sending Response to Request ID: %s on %s",
                            response.request_message_id, request.destination_topic)
                client.send_response(response)

        # Create DXL Service Registration object
        service_registration_info = ServiceRegistrationInfo(client, "/mycompany/myservice")

        # Add a topic for the service to respond to
        service_registration_info.add_topic(SERVICE_TOPIC, MyRequestCallback())

        # Register the service with the DXL fabric (with a wait up to 10 seconds for registration to complete)
        logger.info("Registering service.")
        client.register_service_sync(service_registration_info, 10)

        # Wait for DXL Requests
        while True:
            print "   Enter 9 to quit"
            input = raw_input("   Enter value: ")

            try:
                option = int(input)
            except:
                option = input

            # Option: Exit the loop
            if option == 9:
                break

            # Invalid input
            else:
                logger.info("Service Provider - Invalid input: %s", option)

except Exception as e:
    logger.info("Service Provider - Exception: %s", e.message)
    exit(1)