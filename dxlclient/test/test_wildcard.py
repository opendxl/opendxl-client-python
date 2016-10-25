# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2014 McAfee Inc. - All Rights Reserved.
################################################################################

# Run with python -m unittest dxlclient.test.test_dxlclient

import unittest

import time

from dxlclient.test.base_test import BaseClientTest
from nose_parameterized import parameterized
from mock import Mock, patch
from threading import Condition

from dxlclient import DxlClient, UuidGenerator, EventCallback, Event, ServiceRegistrationInfo, Response, \
    ResponseCallback
from dxlclient import DxlUtils, WildcardCallback
from dxlclient import DxlClientConfig
from dxlclient import RequestCallback
from dxlclient import Request
from dxlclient._global_settings import *
from nose.plugins.attrib import attr

def topic_splitter(topic):
    if topic is "":
        return "#"
    splitted = topic.split("/")
    if topic[-1] != "#":
        return "/".join(splitted[:-1]) + "/#"
    else:
        if len(topic) is 2:
            return "#"
        return "/".join(splitted[:-2]) + "/#"

class WilcardPerformanceTest(BaseClientTest):

    #
    # Test to determine whether Bug 1060219 - "Performance of Broker degrades when subscribing to channel
    # (with a lot of subscriptions) using wildcards" has been fixed.
    #
    @attr('system')
    def test_wildcard_performance(self):
        with self.create_client() as client:
            client.connect()

            without_wildcard = self.measure_performance(client, True, False)
            with_wildcard =self.measure_performance(client, False, True)
            with_wildcard_topic_exists = self.measure_performance(client, True, True)

            print "without_wildcard: " + str(without_wildcard)
            print "with_wildcard: " + str(with_wildcard)
            print "with_wildcard_topic_exists: " + str(with_wildcard_topic_exists)

            self.assertTrue(with_wildcard < (2 * without_wildcard))

    #
    # Worker associated with test to determine whether Bug 1060219 - "Performance of Broker degrades when
    # subscribing to channel (with a lot of subscriptions) using wildcards" has been fixed.
    #
    def measure_performance(self, client, with_wildcard, topic_exists):
        SUB_COUNT = 10000
        QUERY_MULTIPLIER = 10
        TOPIC_PREFIX = "/topic/" + UuidGenerator.generate_id_as_string() + "/"
        event_count = [0]
        message_ids = set()
        PAYLOAD = UuidGenerator.generate_id_as_string()
        message_id_condition = Condition()

        cb = EventCallback()

        def on_event(event):
            if event.payload == PAYLOAD:
                with message_id_condition:
                    event_count[0] += 1
                    message_ids.add(event.message_id)
                    message_id_condition.notify()
                    if len(message_ids) % SUB_COUNT == 0:
                        print "Messages size: " + str(len(message_ids))

        cb.on_event = on_event
        client.add_event_callback("#", cb, False)

        if with_wildcard:
            client.subscribe(TOPIC_PREFIX + "#")

        for i in range(SUB_COUNT):
            if i % 1000 == 0:
                print "Subscribed: " + str(i)
            client.subscribe(TOPIC_PREFIX + str(i))

        print "Subscribed."

        start_time = time.time()

        for j in range(SUB_COUNT * QUERY_MULTIPLIER):
            evt = Event(TOPIC_PREFIX + str(j % SUB_COUNT + (SUB_COUNT if not topic_exists else 0)))
            evt.payload = PAYLOAD
            client.send_event(evt)


        with message_id_condition:
            while len(message_ids) != SUB_COUNT * QUERY_MULTIPLIER \
                    or event_count[0] != SUB_COUNT * QUERY_MULTIPLIER * (2 if with_wildcard and topic_exists else 1):
                current_event = event_count[0]
                message_id_condition.wait(5)
                if current_event == event_count[0]:
                    self.fail("Event wait timeout")

        self.assertEquals(SUB_COUNT * QUERY_MULTIPLIER, len(message_ids))
        self.assertEquals(SUB_COUNT * QUERY_MULTIPLIER * (2 if with_wildcard and topic_exists else 1), event_count[0])

        return time.time() - start_time

    # Test service-based wilcarding
    # Test the ability to transform events into requests
    # Test wildcarding of events
    @attr('system')
    def test_wildcard_services(self):
        with self.create_client() as client:
            # The request message that the service receives
            service_request_message = []
            # The request message corresponding to the response received by the client
            client_response_message_request = []
            # The event that we received
            client_event_message = []
            # The payload that the service receives
            service_request_message_receive_payload = []

            client.connect()

            info = ServiceRegistrationInfo(client, "myWildcardService")
            meta = {}
            # Transform events mapped to "test/#/" to "request/test/..."
            meta["EventToRequestTopic"] = "/test/#"
            meta["EventToRequestPrefix"] = "/request"
            info.metadata = meta
            rcb = RequestCallback()

            def on_request(request):
                print "## Request in service: " + request.destination_topic + ", " + str(request.message_id)
                print "## Request in service - payload: " + request.payload

                service_request_message.append(request.message_id)
                service_request_message_receive_payload.append(request.payload)

                response = Response(request)
                response.payload = "Request response - Event payload: " + request.payload
                client.send_response(response)

            rcb.on_request = on_request
            info.add_topic("/request/test/#", rcb)

            client.register_service_sync(info, 10)

            evt = Event("/test/bar")

            rcb = ResponseCallback()
            def on_response(response):
                # Only handle the response corresponding to the event we sent
                if response.request_message_id == evt.message_id:
                    print "## received_response: " + response.request_message_id + ", " + response.__class__.__name__
                    print "## received_response_payload: " + response.payload
                    client_response_message_request[0] = response.request_message_id

            rcb.on_response = on_response
            client.add_response_callback("", rcb)

            ecb = EventCallback()
            def on_event(event):
                print "## received event: " + event.destination_topic + ", " + event.message_id
                client_event_message.append(event.message_id)

            ecb.on_event = on_event
            client.add_event_callback("/test/#", ecb)

            # Send our event
            print "## Sending event: " + evt.destination_topic + ", " + evt.message_id
            evt.payload = "Unit test payload"
            client.send_event(evt)

            time.sleep(10)

            # # Make sure the service received the request properly
            # self.assertEquals(evt.message_id, service_request_message[0])
            # # Make sure the service received the request payload from the event properly
            # self.assertEquals(evt.payload, service_request_message_receive_payload[0])
            # Make sure the response we received was for the request message
            # self.assertEquals(evt.message_id, client_response_message_request[0])
            # Make sure we received the correct event
            self.assertEquals(evt.message_id, client_event_message[0])


class WildcardTest(unittest.TestCase):
    def setUp(self):
        mqtt_client_patch = patch('paho.mqtt.client.Client')
        mqtt_client_patch.start()

        self.config = DxlClientConfig(broker_ca_bundle=get_ca_bundle_pem(),
                                      cert_file=get_cert_file_pem(),
                                      private_key=get_dxl_private_key(),
                                      brokers=[])

        self.req_callback = RequestCallback()
        self.req_callback.on_request = Mock()

    def tearDown(self):
        patch.stopall()

    @parameterized.expand([
        (3, "/foo/bar"),
        (4, "/foo/bar/baz"),
        (5, "/foo/bar/baz/"),
        (1, "/#"),
        (0, "#"),
        (1, "")
    ])
    def test_wildcarding_iteration(self, wildcard_number, topic):
        """
        Tests wildcarding iteration (utility method)
        """
        wildcards = []

        # define what is the callback for iteration
        def on_next_wildcard(wildcard):
            wildcards.append(wildcard)

        wildcard_callback = WildcardCallback()
        wildcard_callback.on_next_wildcard = on_next_wildcard

        DxlUtils.iterate_wildcards(wildcard_callback, topic)
        self.assertEquals(wildcard_number, len(wildcards))

        for wildcard in wildcards:
            topic = topic_splitter(topic)
            self.assertEqual(topic, wildcard)

    def test_adding_wildcarded_channel_enables_wildcarding(self):
        dxl_client = DxlClient(self.config)

        dxl_client.add_request_callback("/this/channel/has/wildcard/#", self.req_callback)
        self.assertTrue(dxl_client._request_callbacks.wildcarding_enabled)

    def test_adding_normal_channel_does_not_enable_wildcarding(self):
        dxl_client = DxlClient(self.config)

        dxl_client.add_request_callback("/this/channel/has/no/wildcard/", self.req_callback)
        self.assertFalse(dxl_client._request_callbacks.wildcarding_enabled)

    def test_removing_only_wildcarded_channel_disables_wildcarding(self):
        dxl_client = DxlClient(self.config)

        dxl_client.add_request_callback("/this/channel/has/wildcard/#", self.req_callback)
        dxl_client.add_request_callback("/this/channel/has/no/wildcard/", self.req_callback)
        self.assertTrue(dxl_client._request_callbacks.wildcarding_enabled)

        dxl_client.remove_request_callback("/this/channel/has/wildcard/#", self.req_callback)
        self.assertFalse(dxl_client._request_callbacks.wildcarding_enabled)

    def test_removing_one_of_two_wildcarded_channels_does_not_disable_wildcarding(self):
        dxl_client = DxlClient(self.config)

        dxl_client.add_request_callback("/this/channel/has/wildcard/#", self.req_callback)
        dxl_client.add_request_callback("/this/channel/has/wildcard/too/#", self.req_callback)

        dxl_client.remove_request_callback("/this/channel/has/wildcard/#", self.req_callback)
        self.assertTrue(dxl_client._request_callbacks.wildcarding_enabled)

    def test_messages_are_fired_with_wildcards_enabled(self):
        dxl_client = DxlClient(self.config)

        dxl_client.add_request_callback("/this/channel/has/wildcard/#", self.req_callback)
        dxl_client.add_request_callback("/this/channel/has/wildcard/not/", self.req_callback)
        # Create and process Request
        req = Request(destination_topic="/this/channel/has/wildcard/not/")._to_bytes()
        dxl_client._handle_message("/this/channel/has/wildcard/not/", req)
        # Check that callback was called
        self.assertEqual(self.req_callback.on_request.call_count, 2)

    def test_messages_are_correctly_fired_with_wildcards_disabled(self):
        dxl_client = DxlClient(self.config)

        dxl_client.add_request_callback("/this/channel/has/no/wildcard/", self.req_callback)
        dxl_client.add_request_callback("/this/channel/has/no/wildcard/either/", self.req_callback)
        # Create and process Request
        req = Request(destination_topic="/this/channel/has/no/wildcard/either/")._to_bytes()
        dxl_client._handle_message("/this/channel/has/no/wildcard/either/", req)
        # Check that callback was called
        self.assertEqual(self.req_callback.on_request.call_count, 1)
