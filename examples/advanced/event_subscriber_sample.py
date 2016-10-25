import logging
import os
import sys

from dxlclient.callbacks import EventCallback
from dxlclient.client import DxlClient
from dxlclient.client_config import DxlClientConfig

# Import common logging and configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from common import *

# Configure local logger
logger = logging.getLogger(__name__)

# Sample topic to fire Events on
EVENT_TOPIC = "/isecg/sample/event"

# Sample Event Subscriber
try:
    # Create DxlClientConfig from expected sample configuration file
    logger.info("Event Subscriber - Load DXL config from: %s", CONFIG_FILE)
    config = DxlClientConfig.create_dxl_config_from_file(CONFIG_FILE)

    # Initialize DXL client using our configuration
    logger.info("Event Subscriber - Creating DXL Client")
    with DxlClient(config) as client:

        # Connect to DXL Broker
        logger.info("Event Subscriber - Connecting to Broker")
        client.connect()

        # Event callback class to handle incoming DXL Events
        class MyEventCallback(EventCallback):
            def on_event(self, event):
                # Extract information from Event payload, in this sample we expect it is UTF-8 encoded
                logger.info("Event Subscriber - Event received:\n   Topic: %s\n   Payload: %s",
                            event.destination_topic, event.payload.decode())

        # Add Event callback to DXL client
        logger.info("Adding Event callback function to Topic: %s", EVENT_TOPIC)
        client.add_event_callback(EVENT_TOPIC, MyEventCallback())

        # Wait for DXL Events
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
                logger.info("Event Subscriber - Invalid input: %s", option)

except Exception as e:
    logger.info("Event Subscriber - Exception: %s", e.message)
    exit(1)