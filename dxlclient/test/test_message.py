# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2014 McAfee Inc. - All Rights Reserved.
################################################################################

# Run with python -m unittest dxlclient.test.test_message

import unittest

from dxlclient import Message
from dxlclient import Event
from dxlclient import Request
from dxlclient import Response
from dxlclient import ErrorResponse
from dxlclient import UuidGenerator

from pprint import PrettyPrinter

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

        event = Event(destination_topic="")
        event._source_client_id = source_client_guid
        event._source_broker_id = source_broker_guid
        event.broker_ids = ["{66000000-0000-0000-0000-000000000001}",
                            "{66000000-0000-0000-0000-000000000002}",
                            "{66000000-0000-0000-0000-000000000003}"]
        event.client_ids = ["{25000000-0000-0000-0000-000000000001}",
                            "{25000000-0000-0000-0000-000000000002}",
                            "{25000000-0000-0000-0000-000000000003}"]
        event.payload = str.encode("EVENT")

        pp.pprint(vars(event))
        message = event._to_bytes()
        pp.pprint(message)

        result = Message._from_bytes(message)
        pp.pprint(vars(result))

        assert result.source_client_id == source_client_guid
        assert result.source_broker_id == source_broker_guid
        assert result.broker_ids == ["{66000000-0000-0000-0000-000000000001}",
                                     "{66000000-0000-0000-0000-000000000002}",
                                     "{66000000-0000-0000-0000-000000000003}"]
        assert result.client_ids == ["{25000000-0000-0000-0000-000000000001}",
                                     "{25000000-0000-0000-0000-000000000002}",
                                     "{25000000-0000-0000-0000-000000000003}"]
        assert result.payload == str.encode("EVENT")
        assert result.message_type == Message.MESSAGE_TYPE_EVENT

    def test_event_with_empty_broker_and_client_guids(self):
        source_client_guid = UuidGenerator.generate_id_as_string()
        source_broker_guid = UuidGenerator.generate_id_as_string()

        event = Event(destination_topic="")
        event._source_client_id = source_client_guid
        event._source_broker_id = source_broker_guid
        event.payload = str.encode("EVENT")

        pp.pprint(vars(event))
        message = event._to_bytes()
        pp.pprint(message)

        result = Message._from_bytes(message)
        pp.pprint(vars(result))

        assert isinstance(result.broker_ids, list)
        assert isinstance(result.client_ids, list)

    def test_request(self):
        reply_to_channel = "/mcafee/client/" + UuidGenerator.generate_id_as_string()
        service_guid = UuidGenerator.generate_id_as_string()
        source_client_guid = UuidGenerator.generate_id_as_string()
        source_broker_guid = UuidGenerator.generate_id_as_string()

        request = Request(destination_topic="")
        request.reply_to_topic = reply_to_channel
        request.service_id = service_guid
        request._source_client_id = source_client_guid
        request._source_broker_id = source_broker_guid
        request.broker_ids = ["{66000000-0000-0000-0000-000000000001}",
                              "{66000000-0000-0000-0000-000000000002}",
                              "{66000000-0000-0000-0000-000000000003}"]
        request.client_ids = ["{25000000-0000-0000-0000-000000000001}",
                              "{25000000-0000-0000-0000-000000000002}",
                              "{25000000-0000-0000-0000-000000000003}"]
        request.payload = str.encode("REQUEST")

        pp.pprint(vars(request))
        message = request._to_bytes()
        pp.pprint(message)

        result = Message._from_bytes(message)
        pp.pprint(vars(result))

        assert result.reply_to_topic == reply_to_channel
        assert result.service_id == service_guid
        assert result.source_client_id == source_client_guid
        assert result.source_broker_id == source_broker_guid
        assert result.broker_ids == ["{66000000-0000-0000-0000-000000000001}",
                                     "{66000000-0000-0000-0000-000000000002}",
                                     "{66000000-0000-0000-0000-000000000003}"]
        assert result.client_ids == ["{25000000-0000-0000-0000-000000000001}",
                                     "{25000000-0000-0000-0000-000000000002}",
                                     "{25000000-0000-0000-0000-000000000003}"]
        assert result.payload == str.encode("REQUEST")
        assert result.message_type == Message.MESSAGE_TYPE_REQUEST

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
        request.payload = str.encode("REQUEST")

        pp.pprint(vars(request))
        message = request._to_bytes()
        pp.pprint(message)

        assert request.source_client_id == source_client_guid

        result = Message._from_bytes(message)
        pp.pprint(vars(result))

        response = Response(request=request)
        response.payload = str.encode("RESPONSE")

        pp.pprint(vars(response))
        message = response._to_bytes()
        pp.pprint(message)
        result = Message._from_bytes(message)
        pp.pprint(vars(result))

        assert result.message_type == Message.MESSAGE_TYPE_RESPONSE

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

        assert result.error_code == error_code
        assert result.error_message == error_message
        assert result.message_type == Message.MESSAGE_TYPE_ERROR
