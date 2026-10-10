# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
################################################################################

"""
Test cases for derivatives of the Message class
"""

# Run with python -m unittest dxlclient.test.test_message

from __future__ import absolute_import
import binascii
from pprint import PrettyPrinter
import unittest

from dxlclient import Message
from dxlclient import Event
from dxlclient import Request
from dxlclient import Response
from dxlclient import ErrorResponse
from dxlclient import UuidGenerator

# pylint: disable=missing-docstring


#
# Configure pretty printer
#
PP = PrettyPrinter(indent=2, width=120)


class MessageTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_event(self):
        source_client_guid = UuidGenerator.generate_id_as_string()
        source_broker_guid = UuidGenerator.generate_id_as_string()
        source_broker_ids = ["{66000000-0000-0000-0000-000000000001}",
                             "{66000000-0000-0000-0000-000000000002}",
                             "{66000000-0000-0000-0000-000000000003}"]
        source_client_ids = ["{25000000-0000-0000-0000-000000000001}",
                             "{25000000-0000-0000-0000-000000000002}",
                             "{25000000-0000-0000-0000-000000000003}"]
        source_payload = "EVENT".encode()

        event = Event(destination_topic="")
        event._source_client_id = source_client_guid
        event._source_broker_id = source_broker_guid
        event.broker_ids = source_broker_ids
        event.client_ids = source_client_ids
        event.payload = source_payload

        PP.pprint(vars(event))
        message = event._to_bytes()
        PP.pprint(message)

        result = Message._from_bytes(message)
        PP.pprint(vars(result))

        self.assertEqual(source_client_guid, result.source_client_id)
        self.assertEqual(source_broker_guid, result.source_broker_id)
        self.assertEqual(source_broker_ids, result.broker_ids)
        self.assertEqual(source_client_ids, result.client_ids)
        self.assertEqual(source_payload, result.payload)
        self.assertEqual(Message.MESSAGE_TYPE_EVENT, result.message_type)

    def test_event_with_empty_broker_and_client_guids(self):
        source_client_guid = UuidGenerator.generate_id_as_string()
        source_broker_guid = UuidGenerator.generate_id_as_string()

        event = Event(destination_topic="")
        event._source_client_id = source_client_guid
        event._source_broker_id = source_broker_guid
        event.payload = "EVENT".encode()

        PP.pprint(vars(event))
        message = event._to_bytes()
        PP.pprint(message)

        result = Message._from_bytes(message)
        PP.pprint(vars(result))

        self.assertTrue(isinstance(result.broker_ids, list))
        self.assertTrue(isinstance(result.client_ids, list))

    def test_request(self):
        reply_to_channel = "/mcafee/client/" + UuidGenerator.generate_id_as_string()
        service_guid = UuidGenerator.generate_id_as_string()
        source_client_guid = UuidGenerator.generate_id_as_string()
        source_broker_guid = UuidGenerator.generate_id_as_string()
        source_broker_ids = ["{66000000-0000-0000-0000-000000000001}",
                             "{66000000-0000-0000-0000-000000000002}",
                             "{66000000-0000-0000-0000-000000000003}"]
        source_client_ids = ["{25000000-0000-0000-0000-000000000001}",
                             "{25000000-0000-0000-0000-000000000002}",
                             "{25000000-0000-0000-0000-000000000003}"]
        source_payload = "REQUEST".encode()

        request = Request(destination_topic="")
        request.reply_to_topic = reply_to_channel
        request.service_id = service_guid
        request._source_client_id = source_client_guid
        request._source_broker_id = source_broker_guid
        request.broker_ids = source_broker_ids
        request.client_ids = source_client_ids
        request.payload = source_payload

        PP.pprint(vars(request))
        message = request._to_bytes()
        PP.pprint(message)

        result = Message._from_bytes(message)
        PP.pprint(vars(result))

        self.assertEqual(reply_to_channel, result.reply_to_topic)
        self.assertEqual(service_guid, result.service_id)
        self.assertEqual(source_client_guid, result.source_client_id)
        self.assertEqual(source_broker_guid, result.source_broker_id)
        self.assertEqual(source_broker_ids, result.broker_ids)
        self.assertEqual(source_client_ids, result.client_ids)
        self.assertEqual(source_payload, result.payload)
        self.assertEqual(Message.MESSAGE_TYPE_REQUEST, result.message_type)

    def test_request_and_response(self):
        reply_to_channel = "/mcafee/client/" + UuidGenerator.generate_id_as_string()
        service_guid = UuidGenerator.generate_id_as_string()
        source_client_guid = UuidGenerator.generate_id_as_string()
        source_broker_guid = UuidGenerator.generate_id_as_string()

        request = Request(destination_topic="")
        request.reply_to_channel = reply_to_channel
        request.service_id = service_guid
        request._source_client_id = source_client_guid
        request._source_broker_id = source_broker_guid
        request.broker_ids = ["{66000000-0000-0000-0000-000000000001}",
                              "{66000000-0000-0000-0000-000000000002}",
                              "{66000000-0000-0000-0000-000000000003}"]
        request.client_ids = ["{25000000-0000-0000-0000-000000000001}",
                              "{25000000-0000-0000-0000-000000000002}",
                              "{25000000-0000-0000-0000-000000000003}"]
        request.payload = "REQUEST".encode()

        PP.pprint(vars(request))
        message = request._to_bytes()
        PP.pprint(message)

        self.assertEqual(source_client_guid, request.source_client_id)

        result = Message._from_bytes(message)
        PP.pprint(vars(result))

        response = Response(request=request)
        response.payload = "RESPONSE".encode()

        PP.pprint(vars(response))
        message = response._to_bytes()
        PP.pprint(message)
        result = Message._from_bytes(message)
        PP.pprint(vars(result))

        self.assertEqual(Message.MESSAGE_TYPE_RESPONSE, result.message_type)

    def test_error_response(self):
        error_code = 99
        error_message = "This is an error"

        response = ErrorResponse(request=None,
                                 error_code=error_code,
                                 error_message=error_message)

        PP.pprint(vars(response))
        message = response._to_bytes()
        PP.pprint(message)

        result = Message._from_bytes(message)
        PP.pprint(vars(result))

        self.assertEqual(error_code, result.error_code)
        self.assertEqual(error_message, result.error_message)
        self.assertEqual(Message.MESSAGE_TYPE_ERROR, result.message_type)


def _populate_message(message):
    message._message_id = "m1"
    message._source_client_id = "c1"
    message._source_broker_id = "b1"
    message.broker_ids = ["b2"]
    message.client_ids = ["c2"]
    message.other_fields = {"k": "v"}
    message.source_tenant_guid = "t1"
    message.destination_tenant_guids = ["t2"]
    message.payload = b"\x00\xff"
    return message


def _create_messages():
    request = _populate_message(Request(destination_topic="/t"))
    request.reply_to_topic = "/r"
    request.service_id = "s1"
    return {
        "request": request,
        "response": _populate_message(Response(request=request)),
        "error": _populate_message(ErrorResponse(request=request, error_code=99,
                                                 error_message="err")),
        "event": _populate_message(Event(destination_topic="/t")),
    }


class MessageWireFormatTest(unittest.TestCase):
    """
    Verifies that the serialized form of each message type does not depend on
    the installed msgpack version. The expected bytes were produced with
    msgpack 0.5.6 and 0.6.2, which is the format DXL brokers and other DXL
    clients expect.
    """

    EXPECTED_BYTES = {
        "request": "0200a26d31a26331a2623191a2623291a26332a200ff"
                   "a22f72a2733192a16ba176a2743191a27432",
        "response": "0201a26d31a26331a2623191a2623291a26332a200ff"
                    "a26d31a2733192a16ba176a2743191a27432",
        "error": "0203a26d31a26331a2623191a2623291a26332a200ff"
                 "a26d31a2733163a365727292a16ba176a2743191a27432",
        "event": "0202a26d31a26331a2623191a2623291a26332a200ff"
                 "92a16ba176a2743191a27432",
    }

    def test_to_bytes_matches_expected_wire_format(self):
        for name, message in _create_messages().items():
            actual = binascii.hexlify(message._to_bytes()).decode()
            self.assertEqual(self.EXPECTED_BYTES[name], actual, name)

    def test_from_bytes_decodes_expected_wire_format(self):
        for name, raw in self.EXPECTED_BYTES.items():
            result = Message._from_bytes(binascii.unhexlify(raw))
            self.assertEqual("m1", result.message_id, name)
            self.assertEqual("c1", result.source_client_id, name)
            self.assertEqual("b1", result.source_broker_id, name)
            self.assertEqual(["b2"], result.broker_ids, name)
            self.assertEqual(["c2"], result.client_ids, name)
            self.assertEqual({"k": "v"}, result.other_fields, name)
            self.assertEqual("t1", result.source_tenant_guid, name)
            self.assertEqual(["t2"], result.destination_tenant_guids, name)
            self.assertEqual(b"\x00\xff", result.payload, name)

        request = Message._from_bytes(binascii.unhexlify(self.EXPECTED_BYTES["request"]))
        self.assertEqual("/r", request.reply_to_topic)
        self.assertEqual("s1", request.service_id)

        response = Message._from_bytes(binascii.unhexlify(self.EXPECTED_BYTES["response"]))
        self.assertEqual("m1", response.request_message_id)
        self.assertEqual("s1", response.service_id)

        error = Message._from_bytes(binascii.unhexlify(self.EXPECTED_BYTES["error"]))
        self.assertEqual(99, error.error_code)
        self.assertEqual("err", error.error_message)

    def test_round_trip_with_non_ascii_strings(self):
        event = _populate_message(Event(destination_topic="/t"))
        event.other_fields = {u"cl\u00e9": u"val\u00fc\u20ac"}
        event.payload = u"\u00e9v\u00e9nement".encode("utf8")

        result = Message._from_bytes(event._to_bytes())

        self.assertEqual({u"cl\u00e9": u"val\u00fc\u20ac"}, result.other_fields)
        self.assertEqual(u"\u00e9v\u00e9nement".encode("utf8"), result.payload)
