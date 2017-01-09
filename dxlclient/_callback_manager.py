# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2017 McAfee Inc. - All Rights Reserved.
################################################################################

import threading
import types

from dxlclient import _BaseObject
from dxlclient.callbacks import MessageCallback, RequestCallback, ResponseCallback, EventCallback
from dxlclient._dxl_utils import WildcardCallback, DxlUtils


def _has_wildcard(channel_name):
    """
    Return whether the channel has a wildcard

    :param channel_name: The channel name
    :return: Whether the channel has a wildcard
    """
    if not  isinstance(channel_name, str):
        raise ValueError("Channel name should be str class")
    return channel_name and channel_name[-1] == '#'


class _CallbackManager(_BaseObject):
    def __init__(self):
        super(_CallbackManager, self).__init__()

        # Read write lock for handling registration and firing concurrency
        self.lock = threading.RLock()
        # Map containing registered listeners by channel name (empty indicates all channels)
        self.callbacks_by_channel = {}
        # Is wildcarding enabled
        self.wildcarding_enabled = False

    def validate_callback(self, callback):  # pylint: disable=no-self-use
        """
        Validates if `callback` is a valid MessageCallback.

        :param callback: Callback to validate.
        """
        if callback is None:
            raise ValueError("Missing callback argument")
        # Check if the provided eventCallback is a class
        if isinstance(callback, (type, types.ClassType)):
            if not issubclass(callback, MessageCallback):
                raise ValueError("Type mismatch on callback argument")
        # Not a class, but an instance
        else:
            if not issubclass(callback.__class__, MessageCallback):
                raise ValueError("Type mismatch on callback argument")

    def add_callback(self, channel="", callback=None):
        """
        Adds the specified callback. The callback will receive messages that were received
        via the specified channel

        :param channel: Limits messages sent to the callback that were received via this channel
        :param callback: The callback to add
        :return: True if the callback was added successfully; False otherwise
        """
        if channel is None:
            raise ValueError("Missing channel argument")

        self.validate_callback(callback)

        rc = False  # pylint: disable=invalid-name
        with self.lock:
            if _has_wildcard(channel):
                self.wildcarding_enabled = True
            callbacks = self.callbacks_by_channel.get(channel)
            if callbacks is None:
                callbacks = []
            if not callback in callbacks:
                callbacks.append(callback)
                self.callbacks_by_channel[channel] = callbacks
                rc = True  # pylint: disable=invalid-name
        return rc

    def remove_callback(self, channel="", callback=None):
        """
        Removes the callback that was registered for the specified channel.

        :param channel: The channel name
        :param callback: The callback to remove
        :return: True if the callback was removed successfully; False otherwise
        """
        if channel is None:
            raise ValueError("Missing channel argument")

        self.validate_callback(callback)

        rc = False  # pylint: disable=invalid-name
        with self.lock:
            callbacks = self.callbacks_by_channel.get(channel)
            if callbacks is not None:
                callbacks.remove(callback)
                if len(callbacks) == 0:
                    del self.callbacks_by_channel[channel]
                else:
                    self.callbacks_by_channel[channel] = callbacks
                rc = True  # pylint: disable=invalid-name

            #Determine if any wildcard exist
            if self.wildcarding_enabled:
                self.wildcarding_enabled = False
                for current_channel_name in self.callbacks_by_channel.keys():
                    if _has_wildcard(current_channel_name):
                        self.wildcarding_enabled = True
                        break
        return rc

    def fire_message(self, message):
        """
        Fires the specified message to the appropriate (taking into consideration
        channel) registered listeners.

        :param message: The message to fire
        :return: None
        """
        with self.lock:
            # Fire for global listeners (channel="")
            self._fire_message(self.callbacks_by_channel.get(""), message)
            # Fire for channel listeners
            self._fire_message(self.callbacks_by_channel.get(message.destination_topic), message)
            #Fire for all wildcarded channels
            # If wildcarding is enabled the message will be fired to each of the message's destination
            # wildcards, if such wildcard exists.
            if self.wildcarding_enabled:

                def on_next_wildcard(wildcard):
                    #if wildcarded channel does not exist no message is fired
                    self._fire_message(self.callbacks_by_channel.get(wildcard), message)

                wildcard_callback = WildcardCallback()
                wildcard_callback.on_next_wildcard = on_next_wildcard

                #Iterate over all channel wildcards sending messages via callback if
                DxlUtils.iterate_wildcards(wildcard_callback, message.destination_topic)

    def _fire_message(self, callbacks, message):
        """
        Fires the message to the specified set of callbacks.

        :param callbacks: The callbacks to fire the message to
        :param message: The message to fire
        :return:
        """
        if callbacks is None or len(callbacks) == 0:
            return

        for callback in callbacks:
            self.handle_fire(callback, message)

    def handle_fire(self, callback, message):
        """
        Method that is to be overridden by derived classes to fire the message to the
        specified callback.

        :param callback: The target of the message
        :param message: The message
        """
        pass


class _RequestCallbackManager(_CallbackManager):
    """
    Manager for {@link RequestCallback} message callbacks.
    """

    def validate_callback(self, callback):
        """
        Validates if `callback` is a valid RequestCallback.

        :param callback: Callback to validate.
        """
        super(_RequestCallbackManager, self).validate_callback(callback)
        # Check if the provided callback is a class
        if isinstance(callback, (type, types.ClassType)):
            if not issubclass(callback, RequestCallback):
                raise ValueError("Type mismatch on callback argument")
        # Not a class, but an instance
        else:
            if not issubclass(callback.__class__, RequestCallback):
                raise ValueError("Type mismatch on callback argument")

    def handle_fire(self, request_callback, request):
        """
        Runs `request_callback` for `request`.

        :param request_callback: {@link dxlclient.callbacks.RequestCallback} object that will handle the event.
        :param request: {@link dxlclient.request.Request} object.
        """
        # Check if the provided eventCallback is a class
        if isinstance(request_callback, (type, types.ClassType)):
            callback = request_callback()
            callback.on_request(request)
        # Not a class, but an instance
        else:
            request_callback.on_request(request)


class _ResponseCallbackManager(_CallbackManager):
    """
    Manager for {@link ResponseCallback} message callbacks.
    """

    def validate_callback(self, callback):
        """
        Validates if `callback` is a valid ResponseCallback.

        :param callback: Callback to validate.
        """
        super(_ResponseCallbackManager, self).validate_callback(callback)
        # Check if the provided callback is a class
        if isinstance(callback, (type, types.ClassType)):
            if not issubclass(callback, ResponseCallback):
                raise ValueError("Type mismatch on callback argument")
        # Not a class, but an instance
        else:
            if not issubclass(callback.__class__, ResponseCallback):
                raise ValueError("Type mismatch on callback argument")

    def handle_fire(self, response_callback, response):
        """
        Runs `response_callback` for `response`.

        :param response_callback: {@link dxlclient.callbacks.ResponseCallback} object that will handle the event.
        :param response: {@link dxlclient.response.Response} object.
        """
        # Check if the provided eventCallback is a class
        if isinstance(response_callback, (type, types.ClassType)):
            callback = response_callback()
            callback.on_response(response)
        # Not a class, but an instance
        else:
            response_callback.on_response(response)


class _EventCallbackManager(_CallbackManager):
    """
    Manager for {@link EventCallback} message callbacks.
    """

    def validate_callback(self, callback):
        """
        Validates if `callback` is a valid EventCallback.

        :param callback: Callback to validate.
        """
        super(_EventCallbackManager, self).validate_callback(callback)
        # Check if the provided callback is a class
        if isinstance(callback, (type, types.ClassType)):
            if not issubclass(callback, EventCallback):
                raise ValueError("Type mismatch on callback argument")
        # Not a class, but an instance
        else:
            if not issubclass(callback.__class__, EventCallback):
                raise ValueError("Type mismatch on callback argument")

    def handle_fire(self, event_callback, event):
        """
        Runs `event_callback` for `event`.

        :param event_callback: {@link dxlclient.callbacks.EventCallback} object that will handle the event.
        :param event: {@link dxlclient.event.Event} object.
        """
        # Check if the provided eventCallback is a class
        if isinstance(event_callback, (type, types.ClassType)):
            callback = event_callback()
            callback.on_event(event)
        # Not a class, but an instance
        else:
            event_callback.on_event(event)
