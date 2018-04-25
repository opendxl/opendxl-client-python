# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
################################################################################

"""
Contains the :class:`RequestManager` class, which handles outgoing requests to
the DXL fabric.
"""

from __future__ import absolute_import
import threading
import time
import logging

from dxlclient.exceptions import WaitTimeoutException
from dxlclient.callbacks import ResponseCallback

logger = logging.getLogger(__name__)


class RequestManager(ResponseCallback):
    """
    Manager that tracks outstanding requests and notifies the appropriate parties
    (invoking a response callback, notifying a waiting object, etc.) when a corresponding
    response is received.

    This purpose of this object is to collaborate with an {@link DxlClient}
    instance.
    """
    # TODO: Add TTL to removed callbacks if response is never received.
    # TODO: Remove current message identifiers if response is never received.

    def __init__(self, client):
        """Constructor"""
        super(RequestManager, self).__init__()

        # Map containing {@link ResponseCallback} instances associated with the
        # identifier of the request message that they are waiting for a response
        # to. This map is used for asynchronous requests.
        self.callback_map = {}
        # Lock for request threads waiting for a response (for synchronous request)
        self.sync_wait_message_lock = threading.RLock()
        # The condition associated with the request threads waiting for a response
        # (for synchronous request).
        self.sync_wait_message_condition = threading.Condition(self.sync_wait_message_lock)
        # Set of identifiers of request messages that are waiting for a response
        # (for synchronous request).
        self.sync_wait_message_ids = set()
        # Messages that have been received mapped by the corresponding request
        # message identifier (for synchronous request).
        self.sync_wait_message_responses = {}
        # Lock for the current request message identifiers (requests that are in process)
        self.current_request_message_lock = threading.RLock()
        # Current request message identifiers (requests that are in process)
        self.current_request_message_ids = set()
        # The client that the request manager is associated with
        self.client = client
        # Register self as ResponseCallback for all channels
        self.client.add_response_callback("", self)

    def destroy(self):
        """Destroys the service manager (releases resources)"""
        self.client = None

    def add_current_request(self, message_id):
        """
        Adds the specified message identifier to the "current" set of requests
        (requests that are in process).
        :param message_id: The request message identifier
        :return: None
        """
        with self.current_request_message_lock:
            if not message_id in self.current_request_message_ids:
                self.current_request_message_ids.add(message_id)

    def remove_current_request(self, message_id):
        """
        Removes the specified message identifier from the "current" set of requests
        (requests that are in process).
        :param message_id: The request message identifier
        :return: None
        """
        with self.current_request_message_lock:
            if message_id in self.current_request_message_ids:
                self.current_request_message_ids.remove(message_id)

    def get_current_request_queue_size(self):
        """
        Returns the size of the current request queue
        :return: The size of the current request queue
        """
        with self.current_request_message_lock:
            return len(self.current_request_message_ids)

    def sync_request(self, request, wait):
        """
        Performs a synchronous request with the default timeout via the DXL fabric
        :param request: The request
        :param wait_ms: The maximum time to wait for the request
        :return: The Response object
        """
        response = None
        self.register_wait_for_response(request)
        try:
            try:
                # Add to set of current requests
                self.add_current_request(request.message_id)
                self.client._send_request(request)
                response = self.wait_for_response(request, wait)
            finally:
                # Remove from set of current requests
                self.remove_current_request(request.message_id)
        finally:
            self.unregister_wait_for_response(request)

        return response

    def async_request(self, request, response_callback):
        """
        Performs an asynchronous request via the DXL fabric
        :param request: The request
        :param response_callback: The callback to be invoked when the response is received
        :return: None
        """
        destination = request.destination_topic
        if not response_callback is None:
            self.register_async_callback(request, response_callback)
        try:
            # Add to set of current requests
            self.add_current_request(request.message_id)
            self.client._send_request(request)
        except Exception:
            try:
                if not response_callback is None:
                    self.unregister_async_callback(destination)
            finally:
                self.remove_current_request(request.message_id)
            raise

    def register_wait_for_response(self, request):
        """
        Indicates to the request manager that you are about to wait for the specified
        request (synchronous response). The registration has to occur prior to actually
        sending the request message to account for the possibility of the response being
        received immediately.
        :param request: The request that is about to be waited for.
        :return: None
        """
        with self.sync_wait_message_lock:
            self.sync_wait_message_ids.add(request.message_id)


    def unregister_wait_for_response(self, request):
        """
        Indicates to the request manager that you no longer want to wait for the specified
        request (synchronous response). This must be invoked when an error occurs while
        waiting for the response, or the response was received.
        :param request: The request that should no longer be waited for
        :return: None
        """
        with self.sync_wait_message_lock:
            if request.message_id in self.sync_wait_message_ids:
                self.sync_wait_message_ids.remove(request.message_id)
            if request.message_id in self.sync_wait_message_responses:
                del self.sync_wait_message_responses[request.message_id]

    def register_async_callback(self, request, response_callback):
        """
        Registers an asynchronous callback for the specified request
        :param request: The request
        :param response_callback: The callback to invoke when the response to request is received.
        :return: None
        """
        self.callback_map[request.message_id] = response_callback

    def unregister_async_callback(self, message_id):
        """
        Removes an asynchronous callback for the specified request
        :param message_id: The identifier for the request
        :return: The response callback or None, if not available
        """
        if message_id in self.callback_map:
            response_callback = self.callback_map[message_id]
            del self.callback_map[message_id]
        else:
            response_callback = None
        return response_callback

    def _get_async_callback_count(self):
        """
        Returns the count of async callbacks that are waiting for a response
        :return: The count of async callbacks that are waiting for a response
        """
        return len(self.callback_map)

    def wait_for_response(self, request, wait):
        """
        Waits for a response to the specified request up to the specified wait time
        in milliseconds.
        :param request: The request for which to wait for the response
        :param wait: The maximum time to wait for the request
        :return: The Response object
        """
        message_id = request.message_id

        with self.sync_wait_message_lock:
            wait_seconds = wait
            wait_start = time.time()

            while not message_id in self.sync_wait_message_responses:
                self.sync_wait_message_condition.wait(wait_seconds)
                if (time.time() - wait_start) >= wait_seconds:
                    raise WaitTimeoutException("Timeout waiting for response to message: " + message_id)

            response = self.sync_wait_message_responses[message_id]
            del self.sync_wait_message_responses[message_id]

        return response

    def on_response(self, response):
        """
        Invoked when an Response has been received.
        """
        request_message_id = response.request_message_id
        try:
            # Check for synchronous waits
            with self.sync_wait_message_lock:
                if request_message_id in self.sync_wait_message_ids:
                    self.sync_wait_message_ids.remove(request_message_id)
                    self.sync_wait_message_responses[request_message_id] = response
                    self.sync_wait_message_condition.notifyAll()

            # Check for asynchronous callbacks
            callback = self.unregister_async_callback(request_message_id)
            if not callback is None:
                callback.on_response(response)
        finally:
            # Remove from set of current requests
            self.remove_current_request(request_message_id)
