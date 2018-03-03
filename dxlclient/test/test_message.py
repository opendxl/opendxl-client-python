# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2014 McAfee Inc. - All Rights Reserved.
################################################################################

# Run with python -m unittest dxlclient.test.test_message

from __future__ import absolute_import
from pprint import PrettyPrinter
import unittest

from dxlclient import Message
from dxlclient import Event
from dxlclient import Request
from dxlclient import Response
from dxlclient import ErrorResponse
from dxlclient import UuidGenerator


#
# Configure pretty printer
#
pp = PrettyPrinter(indent=2, width=120)


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

        pp.pprint(vars(event))
        message = event._to_bytes()
        pp.pprint(message)

        result = Message._from_bytes(message)
        pp.pprint(vars(result))

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

        pp.pprint(vars(event))
        message = event._to_bytes()
        pp.pprint(message)

        result = Message._from_bytes(message)
        pp.pprint(vars(result))

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

        pp.pprint(vars(request))
        message = request._to_bytes()
        pp.pprint(message)

        result = Message._from_bytes(message)
        pp.pprint(vars(result))

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

        pp.pprint(vars(request))
        message = request._to_bytes()
        pp.pprint(message)

        self.assertEqual(source_client_guid, request.source_client_id)

        result = Message._from_bytes(message)
        pp.pprint(vars(result))

        response = Response(request=request)
        response.payload = "RESPONSE".encode()

        pp.pprint(vars(response))
        message = response._to_bytes()
        pp.pprint(message)
        result = Message._from_bytes(message)
        pp.pprint(vars(result))

        self.assertEqual(Message.MESSAGE_TYPE_RESPONSE, result.message_type)

    def test_error_response(self):
        error_code = 99
        error_message = "This is an error"

        response = ErrorResponse(request=None,
                                 error_code=error_code,
                                 error_message=error_message)

        pp.pprint(vars(response))
        message = response._to_bytes()
        pp.pprint(message)

        result = Message._from_bytes(message)
        pp.pprint(vars(result))

        self.assertEqual(error_code, result.error_code)
        self.assertEqual(error_message, result.error_message)
        self.assertEqual(Message.MESSAGE_TYPE_ERROR, result.message_type)
