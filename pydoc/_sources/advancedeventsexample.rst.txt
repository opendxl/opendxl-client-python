Advanced Events Sample
======================

Prior to running this sample make sure you have completed the samples configuration step (:doc:`sampleconfig`).

This sample differs from the :doc:`basiceventsexample` by breaking the "event subscriber" and "event publisher"
functionality into two distinct scripts. When executed, each of these scripts will contain a unique instance of
a :class:`dxlclient.client.DxlClient`.

Event Subscriber
****************

The first step is to start the "event subscriber". This script will remain running and receive
:class:`dxlclient.message.Event` messages from the "event publisher".

To start the "event subscriber", execute the ``sample\advanced\event_subscriber_sample.py`` script as follows:

    .. parsed-literal::

        c:\\dxlclient-python-sdk-\ |version|\>python sample\\advanced\\event_subscriber_sample.py

The output should appear similar to the following:

    .. parsed-literal::

        2015-12-30 08:55:44,936 __main__ - INFO - Event Subscriber - Load DXL config from: c:\\dxlclient-python-sdk-\ |version|\\sample/dxlclient.config
        2015-12-30 08:55:44,938 __main__ - INFO - Event Subscriber - Creating DXL Client
        2015-12-30 08:55:44,956 __main__ - INFO - Event Subscriber - Connecting to Broker
        2015-12-30 08:55:44,957 dxlclient.client - INFO - Waiting for broker list...
        2015-12-30 08:55:44,957 dxlclient.client - INFO - Checking brokers...
        2015-12-30 08:55:44,959 dxlclient.client - INFO - Trying to connect...
        2015-12-30 08:55:44,959 dxlclient.client - INFO - Trying to connect to broker {Unique id: mybroker, Host name: mybroker.mcafee.com, IP address: 10.84.221.144, Port: 8883}...
        2015-12-30 08:55:45,224 dxlclient.client - INFO - Connected to broker mybroker
        2015-12-30 08:55:45,226 dxlclient.client - INFO - Launching event loop...
        2015-12-30 08:55:45,226 dxlclient.client - INFO - Connected with result code 0
        2015-12-30 08:55:45,226 dxlclient.client - INFO - Subscribing to /mcafee/client/{1d79d1a9-8efd-41f3-bc2a-bea5a34b9faa}
        2015-12-30 08:55:45,229 __main__ - INFO - Event Subscriber - Subscribing to Topic: /isecg/sample/event
        2015-12-30 08:55:45,229 __main__ - INFO - Adding Event callback function to Topic: /isecg/sample/event
           Enter 9 to quit
           Enter value:

The subscriber will remain running until ``9`` is entered to quit.

Any :class:`dxlclient.message.Event` messages received by the "event publisher" will be displayed in the output.

The code for the subscriber is very similar to what is being used in the :doc:`basiceventsexample`:

    .. code-block:: python

        # Event callback class to handle incoming DXL Events
        class MyEventCallback(EventCallback):
            def on_event(self, event):
                # Extract information from Event payload, in this sample we expect it is UTF-8 encoded
                logger.info("Event Subscriber - Event received:\n   Topic: %s\n   Payload: %s",
                            event.destination_topic, event.payload.decode())

        # Add Event callback to DXL client
        logger.info("Adding Event callback function to Topic: %s", EVENT_TOPIC)
        client.add_event_callback(EVENT_TOPIC, MyEventCallback())

A :class:`dxlclient.callbacks.EventCallback` is registered with the client for a specific topic. By default
:func:`dxlclient.client.DxlClient.add_event_callback` will also subscribe
(:func:`dxlclient.client.DxlClient.subscribe`) to the same topic on the fabric.

Event Publisher
***************

The next step is to start the "event publisher". This script must be executed in a separate command prompt (or shell),
leaving the "event subscriber" running.

To start the "event publisher", execute the ``sample\advanced\event_publisher_sample.py`` script as follows:

    .. parsed-literal::

        c:\\dxlclient-python-sdk-\ |version|\>python sample\\advanced\\event_publisher_sample.py

The output should appear similar to the following:

    .. parsed-literal::

        2015-12-30 09:00:38,076 __main__ - INFO - Event Publisher - Load DXL config from: C:\\dxlclient-python-sdk-\ |version|\\sample/dxlclient.config
        2015-12-30 09:00:38,078 __main__ - INFO - Event Publisher - Creating DXL Client
        2015-12-30 09:00:38,094 __main__ - INFO - Event Publisher - Connecting to Broker
        2015-12-30 09:00:38,095 dxlclient.client - INFO - Waiting for broker list...
        2015-12-30 09:00:38,095 dxlclient.client - INFO - Checking brokers...
        2015-12-30 09:00:38,096 dxlclient.client - INFO - Trying to connect...
        2015-12-30 09:00:38,096 dxlclient.client - INFO - Trying to connect to broker {Unique id: mybroker, Host name: mybroker.mcafee.com, IP address: 10.84.221.144, Port: 8883}...
        2015-12-30 09:00:38,364 dxlclient.client - INFO - Connected to broker mybroker
        2015-12-30 09:00:38,365 dxlclient.client - INFO - Launching event loop...
        2015-12-30 09:00:38,365 dxlclient.client - INFO - Connected with result code 0
        2015-12-30 09:00:38,365 dxlclient.client - INFO - Subscribing to /mcafee/client/{41eae910-2409-4e4b-9a0f-94b54290a2cf}
           Enter 1 to publish a DXL Event
           Enter 9 to quit
           Enter value:

To publish a :class:`dxlclient.message.Event` message, enter ``1``.

Information similar to the following should appear in the "event subscriber" output indicating that the
:class:`dxlclient.message.Event` message was properly received:

    .. code-block:: python

        2015-12-30 09:03:45,444 __main__ - INFO - Event Subscriber - Event received:
           Topic: /isecg/sample/event
           Payload: Sample Event Payload

The publisher will remain running until ``9`` is entered to quit.

The code for the publisher is very similar to what is being used in the :doc:`basiceventsexample`:

    .. code-block:: python

        # Create the Event
        logger.info("Event Publisher - Creating Event for Topic %s", EVENT_TOPIC)
        event = Event(EVENT_TOPIC)

        # Encode string payload as UTF-8
        event.payload = "Sample Event Payload".encode()

        # Publish the Event to the DXL Fabric on the Topic
        logger.info("Event Publisher - Publishing Event to %s", EVENT_TOPIC)
        client.send_event(event)

An :class:`dxlclient.message.Event` event message is created and a payload is assigned. The event
is delivered to the fabric via the :func:`dxlclient.client.DxlClient.send_event` method.

