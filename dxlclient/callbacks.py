# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
################################################################################

""" Classes for the different DXL message callbacks. """

from __future__ import absolute_import
from dxlclient import _BaseObject


class MessageCallback(_BaseObject):
    """
    Base class for the different callbacks
    """
    pass

class EventCallback(MessageCallback):
    """
    Concrete instances of this interface are used to receive :class:`dxlclient.message.Event` messages.

    To receive events, a concrete instance of this callback must be created and registered with a
    :class:`dxlclient.client.DxlClient` instance via the :func:`dxlclient.client.DxlClient.add_event_callback`
    method.

    The following is a simple example of using an event callback:

    .. code-block:: python

        from dxlclient.callbacks import EventCallback

        class MyEventCallback(EventCallback):
            def on_event(self, event):
                print("Received event! " + event.source_client_id)

        dxl_client.add_event_callback("/testeventtopic", MyEventCallback())

    **NOTE:** By default when registering an event callback the client will automatically subscribe
    (:func:`dxlclient.client.DxlClient.subscribe`) to the topic.

    The following demonstrates a client that is sending an event message that would be received by the
    callback above.

    .. code-block:: python

        from dxlclient.message import Event

        # Create the event message
        evt = Event("/testeventtopic")

        # Populate the event payload
        evt.payload = "testing".encode()

        # Send the event
        dxl_client.send_event(evt)
    """

    def on_event(self, event):
        """
        Invoked when an :class:`dxlclient.message.Event` has been received.

        :param event: The :class:`dxlclient.message.Event` message that was received
        """
        raise NotImplementedError("Must be implemented in a child class.")


class RequestCallback(MessageCallback):
    """
    Concrete instances of this interface are used to receive :class:`dxlclient.message.Request` messages.

    Request callbacks are typically used when implementing a "service".

    See :class:`dxlclient.service.ServiceRegistrationInfo` for more information on how to register a
    service.
    """
    def on_request(self, request):
        """
        Invoked when an :class:`dxlclient.message.Request` has been received.

        :param request: The :class:`dxlclient.message.Request` message that was received
        """
        raise NotImplementedError("Must be implemented in a child class.")


class ResponseCallback(MessageCallback):
    """
    Concrete instances of this interface are used to receive :class:`dxlclient.message.Response` messages.

    Response callbacks are typically used when invoking a service asynchronously.

    The following is a simple example of using a response callback with an asynchronous service invocation:

    .. code-block:: python

        from dxlclient.message import Request
        from dxlclient.callbacks import ResponseCallback

        class MyResponseCallback(ResponseCallback):
            def on_response(self, response):
                print("Received response! " + response.service_id)

        request = Request("/testservice/testrequesttopic")
        dxl_client.async_request(request, MyResponseCallback())

    """

    def on_response(self, response):
        """
        Invoked when an :class:`dxlclient.message.Response` has been received.

        :param response: The :class:`dxlclient.message.Response` message that was received
        """
        raise NotImplementedError("Must be implemented in a child class.")
