Advanced Service Sample
=======================

Prior to running this sample make sure you have completed the samples configuration step (:doc:`sampleconfig`).

This sample differs from the :doc:`basicserviceexample` by breaking the "service provider" and "service invoker"
functionality into two distinct scripts. When executed, each of these scripts will contain a unique instance of
a :class:`dxlclient.client.DxlClient`.

Service Provider
****************

The first step is to start the "service provider". This script will remain running and receive
:class:`dxlclient.message.Request` messages from the "service invoker".

To start the "service provider", execute the ``sample\advanced\service_provider_sample.py`` script as follows:

    .. parsed-literal::

        c:\dxlclient-python-sdk-\ |version|\>python sample\\advanced\\service_provider_sample.py

The output should appear similar to the following:

    .. parsed-literal::

        2015-12-30 10:25:32,168 __main__ - INFO - Service Provider - Load DXL config from: c:\dxlclient-python-sdk-\ |version|\\sample/dxlclient.config
        2015-12-30 10:25:32,170 __main__ - INFO - Service Provider - Creating DXL Client
        2015-12-30 10:25:32,187 __main__ - INFO - Service Provider - Connecting to Broker
        2015-12-30 10:25:32,187 dxlclient.client - INFO - Waiting for broker list...
        2015-12-30 10:25:32,188 dxlclient.client - INFO - Checking brokers...
        2015-12-30 10:25:32,190 dxlclient.client - INFO - Trying to connect...
        2015-12-30 10:25:32,190 dxlclient.client - INFO - Trying to connect to broker {Unique id: mybroker, Host name: mybroker.mcafee.com, IP address: 10.84.221.144, Port: 8883}...
        2015-12-30 10:25:32,457 dxlclient.client - INFO - Connected to broker mybroker
        2015-12-30 10:25:32,459 dxlclient.client - INFO - Launching event loop...
        2015-12-30 10:25:32,459 dxlclient.client - INFO - Connected with result code 0
        2015-12-30 10:25:32,460 dxlclient.client - INFO - Subscribing to /mcafee/client/{1b53cd6a-5829-4a76-a913-a120dc59ede7}
        2015-12-30 10:25:32,461 __main__ - INFO - Registering service.
        2015-12-30 10:25:32,463 dxlclient.client - INFO - Message received for topic /mcafee/client/{1b53cd6a-5829-4a76-a913-a120dc59ede7}
           Enter 9 to quit
           Enter value:

The provider will remain running until ``9`` is entered to quit.

Any :class:`dxlclient.message.Request` messages received by the "service invoker" will be displayed in the output.

The code for the provider is very similar to what is being used in the :doc:`basicserviceexample`:

    .. code-block:: python

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

A :class:`dxlclient.callbacks.RequestCallback` is constructed that will be invoked for a specific topic associated
with the service. The callback will send back a :class:`dxlclient.message.Response` for any
:class:`dxlclient.message.Request` messages that are received.

It then creates a :class:`dxlclient.service.ServiceRegistrationInfo` instance and registers the request
callback with it via the :func:`dxlclient.service.ServiceRegistrationInfo.add_topic` method.

Finally it registers the service with the fabric via the :func:`dxlclient.client.DxlClient.register_service_sync`
method of the :class:`dxlclient.client.DxlClient`.

Service Invoker
***************

The next step is to start the "service invoker". This script must be executed in a separate command prompt (or shell),
leaving the "service provider" running.

To start the "service invoker", execute the ``sample\advanced\service_invoker_sample.py`` script as follows:

    .. parsed-literal::

        c:\\dxlclient-python-sdk-\ |version|\>python sample\\advanced\\service_invoker_sample.py

The output should appear similar to the following:

    .. parsed-literal::

        2015-12-30 10:43:33,627 __main__ - INFO - Service Invoker - Load DXL config from: c:\\dxlclient-python-sdk-\ |version|\\sample/dxlclient.config
        2015-12-30 10:43:33,628 __main__ - INFO - Service Invoker - Creating DXL Client
        2015-12-30 10:43:33,644 __main__ - INFO - Service Invoker - Connecting to Broker
        2015-12-30 10:43:33,645 dxlclient.client - INFO - Waiting for broker list...
        2015-12-30 10:43:33,645 dxlclient.client - INFO - Checking brokers...
        2015-12-30 10:43:33,648 dxlclient.client - INFO - Trying to connect...
        2015-12-30 10:43:33,648 dxlclient.client - INFO - Trying to connect to broker {Unique id: mybroker, Host name: mybroker.mcafee.com, IP address: 10.84.221.144, Port: 8883}...
        2015-12-30 10:43:33,917 dxlclient.client - INFO - Connected to broker mybroker
        2015-12-30 10:43:33,918 dxlclient.client - INFO - Launching event loop...
        2015-12-30 10:43:33,920 dxlclient.client - INFO - Connected with result code 0
        2015-12-30 10:43:33,920 dxlclient.client - INFO - Subscribing to /mcafee/client/{9ee95507-0c73-4696-a628-6a89e2a79194}
           Press 1 to send a Synchronous Request
           Press 2 to send an Asynchronous Request
           Press 9 to quit
           Enter value:

To publish a synchronous :class:`dxlclient.message.Request` message, enter ``1``.

To publish an asynchronous :class:`dxlclient.message.Request` message, enter ``2``.

Information similar to the following should appear in the "service provider" output indicating that the
:class:`dxlclient.message.Request` message was properly received and that a corresponding
:class:`dxlclient.message.Response` message was sent:

    .. code-block:: python

        2015-12-30 10:44:59,832 __main__ - INFO - Service Provider - Request received:
           Topic: /isecg/sample/service
           Request ID: {0e7c1994-b610-4436-ae3b-e2eec9ebdf33}
           Payload: Sample Synchronous Request Payload - Request ID: {0e7c1994-b610-4436-ae3b-e2eec9ebdf33}
        2015-12-30 10:44:59,834 __main__ - INFO - Service Provider - Creating Response for Request ID {0e7c1994-b610-4436-ae3b-e2eec9ebdf33} on /isecg/sample/service
        2015-12-30 10:44:59,835 __main__ - INFO - Service Provider - Sending Response to Request ID: {0e7c1994-b610-4436-ae3b-e2eec9ebdf33} on /isecg/sample/service

Information similar to the following should appear in the "service invoker" output indicating that the
:class:`dxlclient.message.Response` message was properly received:

    .. code-block:: python

        2015-12-30 10:44:59,838 dxlclient.client - INFO - Message received for topic /mcafee/client/{9ee95507-0c73-4696-a628-6a89e2a79194}
        2015-12-30 10:44:59,845 __main__ - INFO - Service Invoker - Synchronous Response received:
           Topic: /mcafee/client/{9ee95507-0c73-4696-a628-6a89e2a79194}
           Payload: Sample Response Payload


The code for making *synchronous requests* is very similar to what is being used in the :doc:`basicserviceexample`:

    .. code-block:: python

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

A :class:`dxlclient.message.Request` message is constructed and a payload is assigned. The
:func:`dxlclient.client.DxlClient.sync_request` method of the :class:`dxlclient.client.DxlClient` is
invoked which delivers the request message to the fabric. The :class:`dxlclient.message.Response`
message is checked to ensure it is not an error, and its payload is displayed.

The code for making *asynchronous requests* is listed below:

    .. code-block:: python

        # Response callback class to handle DXL Responses from a Service to our Asynchronous Requests
        class MyResponseCallback(ResponseCallback):
            def on_response(self, response):
                # Check that the Response is not an Error Response, then extract
                if response.message_type != Message.MESSAGE_TYPE_ERROR:
                    # Extract information from Response payload, in this sample we expect it is UTF-8 encoded
                    logger.info("Service Invoker - Asynchronous Response received:\n   " +
                                "Topic: %s\n   Request ID: %s\n   Payload: %s",
                                response.destination_topic, response.request_message_id, response.payload.decode())
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

A :class:`dxlclient.callbacks.ResponseCallback` is defined that will receive the :class:`dxlclient.message.Response`
message from the service provider. The callback will display the details of the response message that was
received (including validating that it is not an error response).

A :class:`dxlclient.message.Request` message is constructed and a payload is assigned. The
:func:`dxlclient.client.DxlClient.async_request` method of the :class:`dxlclient.client.DxlClient` is
invoked which delivers the request message to the fabric. Along with the request, an instance of
the previously defined response callback is included which will be invoked when a response is received
from the service provider.
