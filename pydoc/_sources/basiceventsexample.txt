Basic Events Sample
===================

This sample demonstrates how to register a callback to receive :class:`dxlclient.message.Event` messages
from the DXL fabric. Once the callback is registered, the sample sends a set number of
:class:`dxlclient.message.Event` messages to the fabric and waits for them all to be received by
the callback.

Prior to running this sample make sure you have completed the samples configuration step (:doc:`sampleconfig`).

To run this sample execute the ``sample\basic\event_example.py`` script as follows:

    .. parsed-literal::

        c:\\dxlclient-python-sdk-\ |version|\>python sample\\basic\\event_example.py

The output should appear similar to the following:

    .. code-block:: python

        Received event: 0
        Received event: 1
        Received event: 2
        Received event: 3
        Received event: 4
        Received event: 5

        ...

        Received event: 994
        Received event: 995
        Received event: 996
        Received event: 997
        Received event: 998
        Received event: 999
        Elapsed time (ms): 441.999912262

The code for the sample is broken into two main sections.

The first section is responsible for registering an :class:`dxlclient.callbacks.EventCallback` for a specific
topic. The :func:`dxlclient.client.DxlClient.add_event_callback` by default will also
subscribe (:func:`dxlclient.client.DxlClient.subscribe`) to the topic.

    .. code-block:: python

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

The second section sends a set amount of :class:`dxlclient.message.Event` messages via the
:func:`dxlclient.client.DxlClient.send_event` method of the :class:`dxlclient.client.DxlClient`.

It then waits for all of the events to be received by the :class:`dxlclient.callbacks.EventCallback` that was
previously registered.

    .. code-block:: python

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
        with event_count_condition:
            while event_count[0] < TOTAL_EVENTS:
                event_count_condition.wait()

        # Print the elapsed time
        print "Elapsed time (ms): " + str((time.time() - start) * 1000)