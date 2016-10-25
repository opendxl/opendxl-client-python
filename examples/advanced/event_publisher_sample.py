import logging
import os
import sys

from dxlclient.client import DxlClient
from dxlclient.client_config import DxlClientConfig
from dxlclient.message import Event

# Import common logging and configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from common import *

# Configure local logger
logger = logging.getLogger(__name__)

# Sample topic to publish DXL Events on
EVENT_TOPIC = "/isecg/sample/event"

# Sample Event Publisher
try:
    # Create DxlClientConfig from expected sample configuration file
    logger.info("Event Publisher - Load DXL config from: %s", CONFIG_FILE)
    config = DxlClientConfig.create_dxl_config_from_file(CONFIG_FILE)

    # Initialize DXL client using our configuration
    logger.info("Event Publisher - Creating DXL Client")
    with DxlClient(config) as client:

        # Connect to DXL Broker
        logger.info("Event Publisher - Connecting to Broker")
        client.connect()

        # Prompt user for input to publish DXL Events
        while True:
            print "   Enter 1 to publish a DXL Event"
            print "   Enter 9 to quit"
            input = raw_input("   Enter value: ")

            try:
                option = int(input)
            except:
                option = input

            # Option: DXL Event
            if option == 1:
                # Create the Event
                logger.info("Event Publisher - Creating Event for Topic %s", EVENT_TOPIC)
                event = Event(EVENT_TOPIC)

                # Encode string payload as UTF-8
                event.payload = "Sample Event Payload".encode()

                # Publish the Event to the DXL Fabric on the Topic
                logger.info("Event Publisher - Publishing Event to %s", EVENT_TOPIC)
                client.send_event(event)

            # Option: Exit the loop
            elif option == 9:
                break

            # Invalid input
            else:
                logger.info("Event Publisher - Invalid input: %s", option)
        # End Prompt Loop

except Exception as e:
    logger.info("Event Publisher - Exception: %s", e.message)
    exit(1)