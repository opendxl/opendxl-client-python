# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2014 McAfee Inc. - All Rights Reserved.
################################################################################

# Run with python -m unittest dxlclient.test.test_request_manager

import unittest

import dxlclient.exceptions as exceptions
from dxlclient.callbacks import ResponseCallback
from dxlclient import RequestManager
from dxlclient import Request
from dxlclient import Response
from dxlclient import UuidGenerator


class MockDxlClient(object):
    def __init__(self):
        # The unique identifier of the client
        self.unique_id = UuidGenerator.generate_id_as_string()

    def add_response_callback(self, channel, response_callback):
        pass

    def _send_request(self, request):
        pass


class MockResponseCallback(ResponseCallback):
    def on_response(self, response):
        pass


class RequestManagerTest(unittest.TestCase):
    def setUp(self):
        self.client = MockDxlClient()
        self.rm = RequestManager(self.client)

    def test_current_request(self):
        uid = UuidGenerator.generate_id_as_string()
        self.rm.add_current_request(uid)
        self.assertEquals(1, self.rm.get_current_request_queue_size())
        self.assertTrue(uid in self.rm.current_request_message_ids)
        self.rm.remove_current_request(uid)
        self.assertEquals(0, self.rm.get_current_request_queue_size())
        self.assertFalse(uid in self.rm.current_request_message_ids)

    def test_register_wait_for_response(self):
        request = Request(destination_topic="/test")
        self.rm.register_wait_for_response(request)
        self.assertEquals(1, len(self.rm.sync_wait_message_ids))
        self.assertTrue(request.message_id in self.rm.sync_wait_message_ids)
        self.rm.unregister_wait_for_response(request)
        self.assertEquals(0, len(self.rm.sync_wait_message_ids))
        self.assertFalse(request.message_id in self.rm.sync_wait_message_ids)

    def test_register_async_callback(self):
        request = Request(destination_topic="/test")
        cb = MockResponseCallback()

        self.rm.register_async_callback(request, cb)
        self.assertTrue(request.message_id in self.rm.callback_map)
        self.rm.unregister_async_callback(request.message_id)
        self.assertFalse(request.message_id in self.rm.callback_map)

    def test_wait_for_response(self):
        request = Request(destination_topic="/test")

        with self.assertRaises(exceptions.WaitTimeoutException):
            self.rm.wait_for_response(request, 2)

    def test_on_response_for_sync_request(self):
        request = Request(destination_topic="/test")
        self.rm.register_wait_for_response(request)

        self.assertEquals(1, len(self.rm.sync_wait_message_ids))
        self.assertTrue(request.message_id in self.rm.sync_wait_message_ids)

        response = Response(request=request)
        self.rm.on_response(response)

        self.assertEquals(0, len(self.rm.sync_wait_message_ids))
        self.assertEquals(1, len(self.rm.sync_wait_message_responses))
        self.assertTrue(request.message_id in self.rm.sync_wait_message_responses)

        result = self.rm.wait_for_response(request, 2)

        self.assertEquals(request.message_id, result.request_message_id)

    def test_sync_request(self):
        request = Request(destination_topic="/test")

        with self.assertRaises(exceptions.WaitTimeoutException):
            self.rm.sync_request(request, 2)

        self.assertEquals(0, len(self.rm.sync_wait_message_ids))
        self.assertEquals(0, len(self.rm.sync_wait_message_responses))

    def test_async_request(self):
        request = Request(destination_topic="/test")

        class TestResponseCallback(ResponseCallback):
            def __init__(self):
                super(TestResponseCallback, self).__init__()
                self.response = None

            def on_response(self, resp):
                self.response = resp

        cb = TestResponseCallback()
        self.assertIsNone(cb.response)

        self.rm.async_request(request, cb)

        self.assertEquals(0, len(self.rm.sync_wait_message_ids))
        self.assertEquals(0, len(self.rm.sync_wait_message_responses))
        self.assertTrue(request.message_id in self.rm.callback_map)

        response = Response(request=request)
        self.rm.on_response(response)

        self.assertIsNotNone(cb.response)
        self.assertEquals(request.message_id, cb.response.request_message_id)

        self.assertEquals(0, len(self.rm.sync_wait_message_ids))
        self.assertEquals(0, len(self.rm.sync_wait_message_responses))
        self.assertFalse(request.message_id in self.rm.callback_map)
