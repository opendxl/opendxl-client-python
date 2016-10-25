import logging
import os
import sys

from dxlclient.callbacks import ResponseCallback
from dxlclient.client import DxlClient
from dxlclient.client_config import DxlClientConfig
from dxlclient.message import Message, Request

# Import common logging and configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from common import *

# Configure local logger
logger = logging.getLogger(__name__)

# Sample topic to fire Requests on
SERVICE_TOPIC = "/isecg/sample/service"

# Sample Synchronous Service Invoker
try:
    # Create DxlClientConfig from expected sample configuration file
    logger.info("Service Invoker - Load DXL config from: %s", CONFIG_FILE)
    config = DxlClientConfig.create_dxl_config_from_file(CONFIG_FILE)

    # Initialize DXL client using our configuration
    logger.info("Service Invoker - Creating DXL Client")
    with DxlClient(config) as client:

        # Connect to DXL Broker
        logger.info("Service Invoker - Connecting to Broker")
        client.connect()

        # Prompt user for input to publish DXL Requests
        while True:
            print "   Press 1 to send a Synchronous Request"
            print "   Press 2 to send an Asynchronous Request"
            print "   Press 9 to quit"
            input = raw_input("   Enter value: ")

            try:
                option = int(input)
            except:
                option = input

            # Option: Synchronous DXL Request
            if option == 1:
                # Create the Request
                logger.info("Service Invoker - Creating Synchronous Request for topic %s", SERVICE_TOPIC)
                request = Request(SERVICE_TOPIC)

                # Encode string payload as UTF-8
                request.payload = ("Sample Synchronous Request Payload - Request ID: " +
                                   str(request.message_id)).encode()

                # Send Synchronous Request with default timeout and wait for Response
                logger.info("Service Invoker - Sending Synchronous Request to %s", SERVICE_TOPIC)
                response = client.sync_request(request)

                # Check that the Response is not an Error Response, then extract
                if response.message_type != Message.MESSAGE_TYPE_ERROR:
                    # Extract information from Response payload, in this sample we expect it is UTF-8 encoded
                    logger.info("Service Invoker - Synchronous Response received:\n   Topic: %s\n   Payload: %s",
                                response.destination_topic,
                                response.payload.decode())
                else:
                    logger.info("Service Invoker - Synchronous Error Response received:\n   Topic: %s\n   Error: %s",
                                response.destination_topic, response.error_message)

            # Option: Asynchronous DXL Request
            elif option == 2:
                # Response callback class to handle DXL Responses from a Service to our Asynchronous Requests
                class MyResponseCallback(ResponseCallback):
                    def on_response(self, response):
                        # Check that the Response is not an Error Response, then extract
                        if response.message_type != Message.MESSAGE_TYPE_ERROR:
                            # Extract information from Response payload, in this sample we expect it is UTF-8 encoded
                            logger.info("Service Invoker - Asynchronous Response received:\n   " +
                                        "Topic: %s\n   Request ID: %s\n   Payload: %s",
                                        response.destination_topic, response.request_message_id,
                                        response.payload.decode())
                        else:
                            logger.info("Service Invoker - Asynchronous Error Response received:\n   " +
                                        "Topic: %s\n   Request ID: %s\n   Error: %s",
                                        response.destination_topic, response.request_message_id, response.error_message)

                # Create the Request
                logger.info("Service Invoker - Creating Asynchronous Request for topic %s", SERVICE_TOPIC)
                request = Request(SERVICE_TOPIC)

                # Encode string payload as UTF-8
                request.payload = 'Sample Asynchronous Request Payload'.encode()

                #Send Asynchronous Request with a timeout of 5 seconds
                logger.info("Service Invoker - Sending Asynchronous Request:\n   Request ID: %s\n   Topic: %s",
                            request.message_id, SERVICE_TOPIC)
                client.async_request(request, MyResponseCallback())

            # Option: Exit the loop
            elif option == 9:
                break

            # Invalid input
            else:
                logger.info("fdsaService Invoker - Invalid input: %s", option)

except Exception as e:
    logger.info("Service Invoker - Exception: %s", e.message)
    exit(1)