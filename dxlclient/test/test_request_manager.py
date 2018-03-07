# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2014 McAfee Inc. - All Rights Reserved.
################################################################################

"""
Test cases for the RequestManager class
"""

# Run with python -m unittest dxlclient.test.test_request_manager

from __future__ import absolute_import
import unittest

import dxlclient.exceptions as exceptions
from dxlclient.callbacks import ResponseCallback
from dxlclient import RequestManager
from dxlclient import Request
from dxlclient import Response
from dxlclient import UuidGenerator

# pylint: disable=missing-docstring


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
        self.request_manager = RequestManager(self.client)

    def test_current_request(self):
        uid = UuidGenerator.generate_id_as_string()
        self.request_manager.add_current_request(uid)
        self.assertEqual(1, self.request_manager.get_current_request_queue_size())
        self.assertTrue(uid in self.request_manager.current_request_message_ids)
        self.request_manager.remove_current_request(uid)
        self.assertEqual(0, self.request_manager.get_current_request_queue_size())
        self.assertFalse(uid in self.request_manager.current_request_message_ids)

    def test_register_wait_for_response(self):
        request = Request(destination_topic="/test")
        self.request_manager.register_wait_for_response(request)
        self.assertEqual(1, len(self.request_manager.sync_wait_message_ids))
        self.assertTrue(request.message_id in self.request_manager.sync_wait_message_ids)
        self.request_manager.unregister_wait_for_response(request)
        self.assertEqual(0, len(self.request_manager.sync_wait_message_ids))
        self.assertFalse(request.message_id in self.request_manager.sync_wait_message_ids)

    def test_register_async_callback(self):
        request = Request(destination_topic="/test")
        callback = MockResponseCallback()

        self.request_manager.register_async_callback(request, callback)
        self.assertTrue(request.message_id in self.request_manager.callback_map)
        self.request_manager.unregister_async_callback(request.message_id)
        self.assertFalse(request.message_id in self.request_manager.callback_map)

    def test_wait_for_response(self):
        request = Request(destination_topic="/test")

        with self.assertRaises(exceptions.WaitTimeoutException):
            self.request_manager.wait_for_response(request, 2)

    def test_on_response_for_sync_request(self):
        request = Request(destination_topic="/test")
        self.request_manager.register_wait_for_response(request)

        self.assertEqual(1, len(self.request_manager.sync_wait_message_ids))
        self.assertTrue(request.message_id in self.request_manager.sync_wait_message_ids)

        response = Response(request=request)
        self.request_manager.on_response(response)

        self.assertEqual(0, len(self.request_manager.sync_wait_message_ids))
        self.assertEqual(1, len(self.request_manager.sync_wait_message_responses))
        self.assertTrue(request.message_id in self.request_manager.sync_wait_message_responses)

        result = self.request_manager.wait_for_response(request, 2)

        self.assertEqual(request.message_id, result.request_message_id)

    def test_sync_request(self):
        request = Request(destination_topic="/test")

        with self.assertRaises(exceptions.WaitTimeoutException):
            self.request_manager.sync_request(request, 2)

        self.assertEqual(0, len(self.request_manager.sync_wait_message_ids))
        self.assertEqual(0, len(self.request_manager.sync_wait_message_responses))

    def test_async_request(self):
        request = Request(destination_topic="/test")

        class TestResponseCallback(ResponseCallback):
            def __init__(self):
                super(TestResponseCallback, self).__init__()
                self.response = None

            def on_response(self, response):
                self.response = response

        callback = TestResponseCallback()
        self.assertIsNone(callback.response)

        self.request_manager.async_request(request, callback)

        self.assertEqual(0, len(self.request_manager.sync_wait_message_ids))
        self.assertEqual(0, len(self.request_manager.sync_wait_message_responses))
        self.assertTrue(request.message_id in self.request_manager.callback_map)

        response = Response(request=request)
        self.request_manager.on_response(response)

        self.assertIsNotNone(callback.response)
        self.assertEqual(request.message_id, callback.response.request_message_id)

        self.assertEqual(0, len(self.request_manager.sync_wait_message_ids))
        self.assertEqual(0, len(self.request_manager.sync_wait_message_responses))
        self.assertFalse(request.message_id in self.request_manager.callback_map)
