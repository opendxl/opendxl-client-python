# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
################################################################################

"""
The messages module contains the different types of messages that are transmitted
over the Data Exchange Layer (DXL) fabric.

- :class:`Event`
- :class:`Request`
- :class:`Response`
- :class:`ErrorResponse`

:class:`Event` messages are sent using the :func:`dxlclient.client.DxlClient.send_event` method of a client instance.
Event messages are sent by one publisher and received by one or more recipients that are currently
subscribed to the :attr:`Message.destination_topic` associated with the event (otherwise known as one-to-many).

:class:`Request` messages are sent using the :func:`dxlclient.client.DxlClient.sync_request` and
:func:`dxlclient.client.DxlClient.async_request` methods of a client instance. Request messages are used when
invoking a method on a remote service. This communication is one-to-one where a client sends a request to a
service instance and in turn receives a response.

:class:`Response` messages are sent by service instances upon receiving :class:`Request` messages. Response messages
are sent using the :func:`dxlclient.client.DxlClient.send_response` method of a client instance. Clients that are
invoking the service (sending a request) will receive the response as a return value of the
:func:`dxlclient.client.DxlClient.sync_request` method of a client instance or via the
:class:`dxlclient.callbacks.ResponseCallback` callback when invoking the asynchronous method,
:func:`dxlclient.client.DxlClient.async_request`.

:class:`ErrorResponse` messages are sent by the DXL fabric itself or service instances upon receiving :class:`Request`
messages. The error response may indicate the inability to locate a service to handle the request or an internal
error within the service itself. Error response messages are sent using the
:func:`dxlclient.client.DxlClient.send_response` method of a client instance.

**NOTE:** Some services may chose to not send a :class:`Response` message when receiving a :class:`Request`.
This typically occurs if the service is being used to simply collect information from remote clients. In this scenario,
the client should use the asynchronous form for sending requests,
:func:`dxlclient.client.DxlClient.async_request`
"""

from __future__ import absolute_import
from io import BytesIO
from abc import ABCMeta, abstractproperty, abstractmethod

import os
os.environ['MSGPACK_PUREPYTHON'] = "1"
# pylint: disable=wrong-import-position
import msgpack

from dxlclient import _BaseObject
from dxlclient._uuid_generator import UuidGenerator
from dxlclient.exceptions import DxlException
from ._compat import iter_dict_items


class Message(ABCMeta('ABC', (_BaseObject,), {'__slots__': ()})): # compatible metaclass with Python 2 *and* 3
    """
    The base class for the different Data Exchange Layer (DXL) message types
    """

    # The message version
    MESSAGE_VERSION = 2

    MESSAGE_TYPE_REQUEST = 0
    """The numeric type identifier for the :class:`Request` message type"""
    MESSAGE_TYPE_RESPONSE = 1
    """The numeric type identifier for the :class:`Response` message type"""
    MESSAGE_TYPE_EVENT = 2
    """The numeric type identifier for the :class:`Event` message type"""
    MESSAGE_TYPE_ERROR = 3
    """The numeric type identifier for the :class:`ErrorResponse` message type"""

    def __init__(self, destination_topic):
        """
        Constructor parameters:

        :param destination_topic: The topic to publish the message to
        """
        super(Message, self).__init__()

        ###########
        # Version 0
        ###########
        # The version of the message
        self._version = self.MESSAGE_VERSION
        # The unique identifier for the message
        self._message_id = UuidGenerator.generate_id_as_string()
        # The identifier for the client that is the source of the message
        self._source_client_id = ""
        # The GUID for the broker that is the source of the message
        self._source_broker_id = ""
        # The channel that the message is published on
        self._destination_topic = destination_topic
        # The payload to send with the message
        self._payload = bytes()
        # The set of broker GUIDs to deliver the message to
        self._broker_ids = []
        # The set of client GUIDs to deliver the message to
        self._client_ids = []

        ###########
        # Version 1
        ###########
        # Other fields: way to add fields to message types
        self._other_fields = {}

        ###########
        # Version 2
        ###########
        # The GUID for the tenant that is the source of the message
        self._source_tenant_guid = ""
        # The set of tenant GUIDs to deliver the message to
        self._destination_tenant_guids = []

    @property
    def version(self):
        """
        The version of the DXL message (used to determine the features that are available)
        """
        return self._version

    @property
    def message_id(self):
        """
        Unique identifier for the message (UUID)
        """
        return self._message_id

    @property
    def destination_topic(self):
        """
        The topic to publish the message to
        """
        return self._destination_topic

    @destination_topic.setter
    def destination_topic(self, topic):
        self._destination_topic = topic

    @property
    def payload(self):
        """
        The application-specific payload of the message (bytes)
        """
        return self._payload

    @payload.setter
    def payload(self, payload):
        self._payload = payload

    @property
    def source_client_id(self):
        """
        The identifier of the DXL client that sent the message (set by the broker that initially receives the message)
        """
        return self._source_client_id

    @property
    def source_broker_id(self):
        """
        The identifier of the DXL broker that the message's originating client is connected to
        (set by the initial broker)
        """
        return self._source_broker_id

    @abstractproperty
    def message_type(self):
        """
        The numeric type of the message
        """
        return None

    @property
    def broker_ids(self):
        """
        The set of broker identifiers that the message is to be routed to. Setting this value will limit
        which brokers the message will be delivered to. This can be used in conjunction with :func:`client_ids`.
        """
        return self._broker_ids

    @broker_ids.setter
    def broker_ids(self, broker_guids=None):
        if broker_guids is None:
            broker_guids = []
        self._broker_ids = broker_guids

    @property
    def client_ids(self):
        """
        The set of client identifiers that the message is to be routed to. Setting this value will limit
        which clients the message will be delivered to. This can be used in conjunction with :func:`broker_ids`.
        """
        return self._client_ids

    @client_ids.setter
    def client_ids(self, client_guids=None):
        if client_guids is None:
            client_guids = []
        self._client_ids = client_guids

    @abstractmethod
    def _pack_message(self, packer, buf):
        """
        Converts the message to an array of bytes and writes them to buf.

        :param packer: Packer object.
        :param buf: Object to which the bytes will be written. Must have a write method.
        """
        buf.write(packer.pack(self._message_id))
        buf.write(packer.pack(self._source_client_id))
        buf.write(packer.pack(self._source_broker_id))
        buf.write(packer.pack(self._broker_ids))
        buf.write(packer.pack(self._client_ids))
        buf.write(packer.pack(self._payload))

    @abstractmethod
    def _unpack_message(self, unpacker):
        """
        Creates a concrete message from `unpacker`.

        :param unpacker: Unpacker object.
        """
        self._message_id = self._unpack_next_unicode_string(unpacker)
        self._source_client_id = self._unpack_next_unicode_string(unpacker)
        self._source_broker_id = self._unpack_next_unicode_string(unpacker)
        self._broker_ids = self._unpack_next_unicode_string_array(unpacker)
        self._client_ids = self._unpack_next_unicode_string_array(unpacker)
        self._payload = next(unpacker)

    @property
    def other_fields(self):
        """
        Returns a ``dict`` (dictionary) containing the set of additional fields associated
        with the message. These fields can be used to add "header" like values to the
        message without requiring modifications to be made to the payload.
        """
        return self._other_fields

    @other_fields.setter
    def other_fields(self, other_fields=None):
        if other_fields is None:
            other_fields = {}
        self._other_fields = other_fields

    @property
    def source_tenant_guid(self):
        """
        The tenant identifier of the DXL client that sent the message
        (set by the broker that initially receives the message)
        """
        return self._source_tenant_guid

    @source_tenant_guid.setter
    def source_tenant_guid(self, source_tenant_guid=None):
        if source_tenant_guid is None:
            source_tenant_guid = ''
        self._source_tenant_guid = source_tenant_guid

    @property
    def destination_tenant_guids(self):
        """
        The set of tenant identifiers that the message is to be routed to. Setting this value will limit
        which clients the message will be delivered to. This can be used in conjunction with :func:`broker_ids`
        and :func:`client_ids`.
        """
        return self._destination_tenant_guids

    @destination_tenant_guids.setter
    def destination_tenant_guids(self, tenant_guids=None):
        if tenant_guids is None:
            tenant_guids = []
        self._destination_tenant_guids = tenant_guids

    def _pack_message_v1(self, packer, buf):
        """
        Packs the v1 message members to the `buffer`

        :param packer: The packer
        :param buf: Object to which the bytes will be written
        """
        # Internally "otherFields" is a dictionary, but it should be packed as a list to send it.
        array = []
        for key, value in iter_dict_items(self._other_fields):
            array.extend((key, value))
        buf.write(packer.pack(array))

    def _unpack_message_v1(self, unpacker):
        """
        Unpacks the v1 members of the message from `unpacker`.

        :param unpacker: The unpacker
        """
        # The "otherFields" member is unpacked as a list format, and then it is converted to a dictionary.
        array = next(unpacker)
        key = None
        self._other_fields = {}
        for curr in array:
            if key:
                self._other_fields[key] = curr.decode('utf8')
                key = None
            else:
                key = curr.decode('utf8')

    def _pack_message_v2(self, packer, buf):
        """
        Packs the v2 message members to the `buffer`

        :param packer: The packer
        :param buf: Object to which the bytes will be written
        """
        buf.write(packer.pack(self._source_tenant_guid))
        buf.write(packer.pack(self._destination_tenant_guids))

    def _unpack_message_v2(self, unpacker):
        """
        Unpacks the v2 members of the message from `unpacker`.

        :param unpacker: The unpacker
        """
        self._source_tenant_guid = self._unpack_next_unicode_string(unpacker)
        self._destination_tenant_guids = self._unpack_next_unicode_string_array(unpacker)

    def _to_bytes(self):
        """
        Converts the message to an array of bytes and returns it.

        :returns: {@code BytesIO} object.
        """
        buf = BytesIO()
        packer = msgpack.Packer()
        buf.write(packer.pack(self.version))
        buf.write(packer.pack(self.message_type))
        # Version 0
        self._pack_message(packer, buf)
        # Version 1
        if self._version > 0:
            self._pack_message_v1(packer, buf)
        # Version 2
        if self._version > 1:
            self._pack_message_v2(packer, buf)
        return buf.getvalue()

    @staticmethod
    def _from_bytes(raw):
        """
        Converts the specified array of bytes to a concrete message instance
        (request, response, error, etc.) and returns it.

        :param raw: {@code list} of bytes.
        :returns: {@link dxlclient.message.Message} object.
        """
        buf = BytesIO(raw)
        buf.seek(0)
        unpacker = msgpack.Unpacker(buf)
        version = next(unpacker)
        message_type = next(unpacker)

        message = None
        if message_type == Message.MESSAGE_TYPE_REQUEST:
            message = Request(destination_topic="")
        elif message_type == Message.MESSAGE_TYPE_ERROR:
            message = ErrorResponse(request=None)
        elif message_type == Message.MESSAGE_TYPE_RESPONSE:
            message = Response(request="")
        elif message_type == Message.MESSAGE_TYPE_EVENT:
            message = Event(destination_topic="")

        if message is not None:
            message._version = version
            # Version 0
            message._unpack_message(unpacker)
            # Version 1
            if message._version > 0:
                message._unpack_message_v1(unpacker)
            # Version 2
            if message._version > 1:
                message._unpack_message_v2(unpacker)
            return message

        raise DxlException("Unknown message type: " + message_type)

    @staticmethod
    def _decode_to_unicode_string(obj):
        return None if obj is None else obj.decode('utf8')

    @staticmethod
    def _unpack_next_unicode_string(unpacker):
        return Message._decode_to_unicode_string(next(unpacker))

    @staticmethod
    def _unpack_next_unicode_string_array(unpacker):
        return [Message._decode_to_unicode_string(x) for x in next(unpacker)]

class Request(Message):
    """
    :class:`Request` messages are sent using the :func:`dxlclient.client.DxlClient.sync_request` and
    :func:`dxlclient.client.DxlClient.async_request` methods of a client instance. Request messages are used when
    invoking a method on a remote service. This communication is one-to-one where a client sends a request to a
    service instance and in turn receives a response.
    """

    def __init__(self, destination_topic):
        """
        Constructor parameters:

        :param destination_topic: The topic to publish the request to
        """
        super(Request, self).__init__(destination_topic)
        # The topic used to reply to this request
        self._reply_to_topic = None
        # The service id
        self._service_id = ""

    @property
    def message_type(self):
        """
        The numeric type of the message
        """
        return Message.MESSAGE_TYPE_REQUEST

    @property
    def reply_to_topic(self):
        """
        The topic that the :class:`Response` to this :class:`Request` will be sent to
        """
        return self._reply_to_topic

    @reply_to_topic.setter
    def reply_to_topic(self, topic):
        self._reply_to_topic = topic

    @property
    def service_id(self):
        """
        The identifier of the service that this request will be routed to. If an identifier is not specified,
        the initial broker that receives the request will select the service to handle the request (round-robin by
        default).
        """
        return self._service_id

    @service_id.setter
    def service_id(self, service_id):
        self._service_id = service_id

    def _pack_message(self, packer, buf):
        """
        Converts the message to an array of bytes and writes them to buf.

        :param packer: Packer object.
        :param buf: Object to which the bytes will be written. Must have a write method.
        """
        super(Request, self)._pack_message(packer, buf)
        buf.write(packer.pack(self._reply_to_topic))
        buf.write(packer.pack(self._service_id))

    def _unpack_message(self, unpacker):
        """
        Creates a concrete message from `unpacker`.

        :param unpacker: Unpacker object.
        """
        super(Request, self)._unpack_message(unpacker)
        self._reply_to_topic = self._unpack_next_unicode_string(unpacker)
        self._service_id = self._unpack_next_unicode_string(unpacker)


class Response(Message):
    """
    :class:`Response` messages are sent by service instances upon receiving :class:`Request` messages. Response messages
    are sent using the :func:`dxlclient.client.DxlClient.send_response` method of a client instance. Clients that are
    invoking the service (sending a request) will receive the response as a return value of the
    :func:`dxlclient.client.DxlClient.sync_request` method of a client instance or via the
    :class:`dxlclient.callbacks.ResponseCallback` callback when invoking the asynchronous method,
    :func:`dxlclient.client.DxlClient.async_request`.
    """

    def __init__(self, request):
        """
        Constructor parameters:

        :param request: The :class:`Request` message that this is a response for
        """
        if isinstance(request, Request):
            super(Response, self).__init__(request.reply_to_topic)
            # The request (only available when sending the response)
            self._request = request
            # The identifier for the request message that this is a response for
            self._request_message_id = request.message_id

            self._service_id = request.service_id
            if request.source_client_id:
                self.client_ids = [request.source_client_id]
            if request.source_broker_id:
                self.broker_ids = [request.source_broker_id]
        else:
            super(Response, self).__init__(destination_topic="")
            # The request (only available when sending the response)
            self._request = None
            # The identifier for the request message that this is a response for
            self._request_message_id = None
            # The identifier of the service that processed the request
            self._service_id = ""

    @property
    def message_type(self):
        """
        The numeric type of the message
        """
        return Message.MESSAGE_TYPE_RESPONSE

    @property
    def request_message_id(self):
        """
        Unique identifier (UUID) for the :class:`Request` message that this message is a
        response for. This is used by the invoking :class:`dxlclient.client.DxlClient` to
        correlate an incoming :class:`Response` message with the :class:`Request` message that
        was initially sent by the client.
        """
        return self._request_message_id

    @property
    def request(self):
        """
        The :class:`Request` message that this is a response for
        """
        return self._request

    @property
    def service_id(self):
        """
        The identifier of the service that sent this response (the service that the corresponding
        :class:`Request` was routed to).
        """
        return self._service_id

    def _pack_message(self, packer, buf):
        """
        Converts the message to an array of bytes and writes them to buf.

        :param packer: Packer object.
        :param buf: Object to which the bytes will be written. Must have a write method.
        """
        super(Response, self)._pack_message(packer, buf)
        buf.write(packer.pack(self._request_message_id))
        buf.write(packer.pack(self._service_id))

    def _unpack_message(self, unpacker):
        """
        Creates a concrete message from `unpacker`.

        :param unpacker: Unpacker object.
        """
        super(Response, self)._unpack_message(unpacker)
        self._request_message_id = self._unpack_next_unicode_string(unpacker)
        self._service_id = self._unpack_next_unicode_string(unpacker)


class Event(Message):
    """
    :class:`Event` messages are sent using the :func:`dxlclient.client.DxlClient.send_event` method of a client instance.
    Event messages are sent by one publisher and received by one or more recipients that are currently
    subscribed to the :attr:`Message.destination_topic` associated with the event (otherwise known as one-to-many).
    """

    @property
    def message_type(self):
        """
        The numeric type of the message
        """
        return Message.MESSAGE_TYPE_EVENT

    # pylint: disable=useless-super-delegation
    def _pack_message(self, packer, buf):
        """
        Converts the message to an array of bytes and writes them to buf.

        :param packer: Packer object.
        :param buf: Object to which the bytes will be written. Must have a write method.
        """
        super(Event, self)._pack_message(packer, buf)

    def _unpack_message(self, unpacker):
        """
        Creates a concrete message from `unpacker`.

        :param unpacker: Unpacker object.
        """
        super(Event, self)._unpack_message(unpacker)
    # pylint: enable=useless-super-delegation

class ErrorResponse(Response):
    """
    :class:`ErrorResponse` messages are sent by the DXL fabric itself or service instances upon receiving
    :class:`Request` messages. The error response may indicate the inability to locate a service to handle the
    request or an internal error within the service itself. Error response messages are sent using the
    :func:`dxlclient.client.DxlClient.send_response` method of a client instance.
    """

    def __init__(self, request, error_code=0, error_message=""):
        """
        Constructor parameters:

        :param request: The :class:`Request` message that this is a response for
        :param error_code: The numeric error code
        :param error_message: The textual error message
        """
        super(ErrorResponse, self).__init__(request)
        # The error code
        self._error_code = error_code
        # The error message
        self._error_message = error_message

    @property
    def error_code(self):
        """
        The numeric error code for the error response
        """
        return self._error_code

    @property
    def error_message(self):
        """
        The textual error message for the error response
        """
        return self._error_message

    @property
    def message_type(self):
        """
        The numeric type of the message
        """
        return Message.MESSAGE_TYPE_ERROR

    def _pack_message(self, packer, buf):
        """
        Converts the message to an array of bytes and writes them to buf.

        :param packer: Packer object.
        :param buf: Object to which the bytes will be written. Must have a write method.
        """
        super(ErrorResponse, self)._pack_message(packer, buf)
        buf.write(packer.pack(self._error_code))
        buf.write(packer.pack(self._error_message))

    def _unpack_message(self, unpacker):
        """
        Creates a concrete message from `unpacker`.

        :param unpacker: Unpacker object.
        """
        super(ErrorResponse, self)._unpack_message(unpacker)
        self._error_code = next(unpacker)
        self._error_message = self._unpack_next_unicode_string(unpacker)
