Basic Service Sample
=====================

This sample demonstrates how to register a DXL service to receive :class:`dxlclient.message.Request`
messages and send :class:`dxlclient.message.Response` messages back to an invoking
:class:`dxlclient.client.DxlClient`.

Prior to running this sample make sure you have completed the samples configuration step (:doc:`sampleconfig`).

To run this sample execute the ``sample\basic\service_example.py`` script as follows:

    .. parsed-literal::

        c:\\dxlclient-python-sdk-\ |version|\>python sample\\basic\\service_example.py

The output should appear similar to the following:

    .. code-block:: python

        Service received request payload: ping
        Client received response payload: pong

The code for the sample is broken into two main sections.

The first section is responsible for creating a :class:`dxlclient.callbacks.RequestCallback` that will be
invoked for a specific topic associated with the service. The callback will send back a
:class:`dxlclient.message.Response` message with a payload of ``pong`` for any
:class:`dxlclient.message.Request` messages that are received.

It then creates a :class:`dxlclient.service.ServiceRegistrationInfo` instance and registers the request
callback with it via the :func:`dxlclient.service.ServiceRegistrationInfo.add_topic` method.

Finally it registers the service with the fabric via the :func:`dxlclient.client.DxlClient.register_service_sync`
method of the :class:`dxlclient.client.DxlClient`.

    .. code-block:: python

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

The second section sends a :class:`dxlclient.message.Request` message to the service
that contains a payload of ``ping`` via the :func:`dxlclient.client.DxlClient.sync_request` method of
the :class:`dxlclient.client.DxlClient`.

The payloads of the :class:`dxlclient.message.Request` and :class:`dxlclient.message.Response` messages
are printed.

    .. code-block:: python

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