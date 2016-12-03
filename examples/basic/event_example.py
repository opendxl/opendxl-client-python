# This sample demonstrates how to register a callback to receive Event messages
# from the DXL fabric. Once the callback is registered, the sample sends a
# set number of Event messages to the fabric and waits for them all to be
# received by the callback.

import logging
import os
import sys
import time
from threading import Condition

from dxlclient.callbacks import EventCallback
from dxlclient.client import DxlClient
from dxlclient.client_config import DxlClientConfig
from dxlclient.message import Event

# Import common logging and configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from common import *

# Configure local logger
logging.getLogger().setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# The topic to publish to
EVENT_TOPIC = "/isecg/sample/basicevent"

# The total number of events to send
TOTAL_EVENTS = 1000

# Condition/lock used to protect changes to counter
event_count_condition = Condition()

# The events received (use an array so we can modify in callback)
event_count = [0]

# Create DXL configuration from file
config = DxlClientConfig.create_dxl_config_from_file(CONFIG_FILE)

# Create the client
with DxlClient(config) as client:

    # Connect to the fabric
    client.connect()

    #
    # Register callback and subscribe
    #

    # Create and add event listener
    class MyEventCallback(EventCallback):
        def on_event(self, event):
            with event_count_condition:
                # Print the payload for the received event
                print "Received event: " + event.payload.decode()
                # Increment the count
                event_count[0] += 1
                # Notify that the count was increment
                event_count_condition.notify_all()

    # Register the callback with the client
    client.add_event_callback(EVENT_TOPIC, MyEventCallback())

    #
    # Send events
    #

    # Record the start time
    start = time.time()

    # Loop and send the events
    for event_id in range(TOTAL_EVENTS):
        # Create the event
        event = Event(EVENT_TOPIC)
        # Set the payload
        event.payload = str(event_id).encode()
        # Send the event
        client.send_event(event)

    # Wait until all events have been received
    print "Waiting for events to be received..."
    with event_count_condition:
        while event_count[0] < TOTAL_EVENTS:
            event_count_condition.wait()

    # Print the elapsed time
    print "Elapsed time (ms): " + str((time.time() - start) * 1000)