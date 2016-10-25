# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2014 McAfee Inc. - All Rights Reserved.
################################################################################

# Run with python -m unittest dxlclient.test.test_dxlclient

import unittest
import time
import threading
from base_test import BaseClientTest
import io
from nose.plugins.attrib import attr
from nose_parameterized import parameterized
from mock import Mock, patch
from textwrap import dedent
import __builtin__

import dxlclient._global_settings
from dxlclient import Request
from dxlclient import Response
from dxlclient import Event
from dxlclient import ErrorResponse
from dxlclient import DxlClient
from dxlclient import DxlClientConfig
from dxlclient import Broker
from dxlclient import UuidGenerator
from dxlclient import EventCallback
from dxlclient import RequestCallback
from dxlclient import ResponseCallback
from dxlclient import DxlException
from dxlclient import BrokerListError
from dxlclient._global_settings import *

CONFIG_DATA_NO_CERTS_SECTION = """
[no_certs]
BrokerCertChain: certchain.pem
CertFile: certfile.pem
PrivateKey: privatekey.pk

[Brokers]
22cdcace-6e8f-11e5-29c0-005056aa56de: 22cdcace-6e8f-11e5-29c0-005056aa56de;8883;dxl-broker-1;10.218.73.206
"""
CONFIG_DATA_NO_CA_OPTION = """
[Certs]
CertFile: certfile.pem
PrivateKey: privatekey.pk

[Brokers]
22cdcace-6e8f-11e5-29c0-005056aa56de: 22cdcace-6e8f-11e5-29c0-005056aa56de;8883;dxl-broker-1;10.218.73.206
"""
CONFIG_DATA_NO_CERT_OPTION = """
[Certs]
BrokerCertChain: certchain.pem
PrivateKey: privatekey.pk

[Brokers]
22cdcace-6e8f-11e5-29c0-005056aa56de: 22cdcace-6e8f-11e5-29c0-005056aa56de;8883;dxl-broker-1;10.218.73.206
"""
CONFIG_DATA_NO_PK_OPTION = """
[Certs]
BrokerCertChain: certchain.pem
CertFile: certfile.pem

[Brokers]
22cdcace-6e8f-11e5-29c0-005056aa56de: 22cdcace-6e8f-11e5-29c0-005056aa56de;8883;dxl-broker-1;10.218.73.206
"""
CONFIG_DATA_NO_BROKERS_SECTION = """
[Certs]
BrokerCertChain: certchain.pem
CertFile: certfile.pem
PrivateKey: privatekey.pk

22cdcace-6e8f-11e5-29c0-005056aa56de: 22cdcace-6e8f-11e5-29c0-005056aa56de;8883;dxl-broker-1;10.218.73.206
"""
CONFIG_DATA_NO_BROKERS_OPTION = """
[Certs]
BrokerCertChain: certchain.pem
CertFile: certfile.pem
PrivateKey: privatekey.pk

[Brokers]
"""


class DxlClientConfigTest(unittest.TestCase):
    @parameterized.expand([
        (None,),
        ("",)
    ])
    def test_config_throws_value_error_for_empty_ca_bundle(self, ca_bundle):
        self.assertRaises(ValueError, DxlClientConfig, broker_ca_bundle=ca_bundle,
                          cert_file=get_cert_file_pem(), private_key=get_dxl_private_key(), brokers=[])

    @parameterized.expand([
        (None,),
        ("",)
    ])
    def test_config_throws_value_error_for_empty_cert_file(self, cert_file):
        self.assertRaises(ValueError, DxlClientConfig,
                          cert_file=cert_file, broker_ca_bundle=get_ca_bundle_pem(), private_key=get_dxl_private_key(),
                          brokers=[])

    def test_get_fastest_broker_gets_the_fastest(self):
        semaphore = threading.Semaphore(0)
        # Mock brokers connect speed
        fast_broker = Mock()
        slow_broker = Mock()

        def connect_to_broker_slow():
            import time

            semaphore.acquire()
            time.sleep(0.1)
            return

        def connect_to_broker_fast():
            semaphore.release()
            return

        slow_broker._connect_to_broker = connect_to_broker_slow
        fast_broker._connect_to_broker = connect_to_broker_fast
        # Create config and add brokers
        config = DxlClientConfig(broker_ca_bundle=get_ca_bundle_pem(),
                                 cert_file=get_cert_file_pem(),
                                 private_key=get_dxl_private_key(),
                                 brokers=[])
        config.brokers.append(fast_broker)
        config.brokers.append(slow_broker)
        # Check that the returned is the fastest
        self.assertEqual(config._get_fastest_broker(), fast_broker)

    def test_get_sorted_broker_list_returns_empty_when_no_brokers(self):
        config = DxlClientConfig(broker_ca_bundle=get_ca_bundle_pem(),
                                 cert_file=get_cert_file_pem(),
                                 private_key=get_dxl_private_key(),
                                 brokers=[])
        self.assertEqual(config._get_sorted_broker_list(), [])

    def test_get_sorted_broker_list_returns_all_brokers(self):
        # Create config
        config = DxlClientConfig(broker_ca_bundle=get_ca_bundle_pem(),
                                 cert_file=get_cert_file_pem(),
                                 private_key=get_dxl_private_key(),
                                 brokers=[])
        # Create mocked brokers
        b1 = Mock()
        b2 = Mock()
        b1._connect_to_broker = b2._connect_to_broker = Mock(return_value=True)
        # Add them to config
        config.brokers.append(b1)
        config.brokers.append(b2)
        # Get all brokers
        l = config._get_sorted_broker_list()
        # Check all brokers are in the list
        self.assertTrue(b1 in l)
        self.assertTrue(b2 in l)

    @parameterized.expand([
        ({"BrokersList": "Actually not a brokers list"},)
    ])
    def test_get_brokers_raises_exception_from_invalid_json(self, policy):
        config = DxlClientConfig(broker_ca_bundle=get_ca_bundle_pem(),
                                 cert_file=get_cert_file_pem(),
                                 private_key=get_dxl_private_key(),
                                 brokers=[])
        with self.assertRaises(BrokerListError):
            config._set_brokers_from_json(policy)

    def test_set_config_from_file_generates_dxl_config(self):
        read_data = """
        [Certs]
        BrokerCertChain: certchain.pem
        CertFile: certfile.pem
        PrivateKey: privatekey.pk

        [Brokers]
        22cdcace-6e8f-11e5-29c0-005056aa56de: 22cdcace-6e8f-11e5-29c0-005056aa56de;8883;dxl-broker-1;10.218.73.206
        """

        with patch.object(__builtin__, 'open', return_value=io.BytesIO(dedent(read_data))):
            client_config = DxlClientConfig.create_dxl_config_from_file("mock_file")
            self.assertEqual(client_config.cert_file, "certfile.pem")
            self.assertEqual(client_config.broker_ca_bundle, "certchain.pem")
            self.assertEqual(client_config.private_key, "privatekey.pk")
            broker = client_config.brokers[0]
            self.assertEqual(broker.host_name, "dxl-broker-1")
            self.assertEqual(broker.ip_address, "10.218.73.206")
            self.assertEqual(broker.port, 8883)
            self.assertEqual(broker.unique_id, "22cdcace-6e8f-11e5-29c0-005056aa56de")

    def test_set_config_wrong_file_raises_exception(self):
        with self.assertRaises(Exception):
            DxlClientConfig.create_dxl_config_from_file("this_file_doesnt_exist.cfg")

    @parameterized.expand([
        (CONFIG_DATA_NO_CERTS_SECTION,),
        (CONFIG_DATA_NO_CA_OPTION,),
        (CONFIG_DATA_NO_CERT_OPTION,),
        (CONFIG_DATA_NO_PK_OPTION,),
    ])
    def test_missing_certs_raises_exception(self, read_data):
        with patch.object(__builtin__, 'open', return_value=io.BytesIO(dedent(read_data))):
            with self.assertRaises(ValueError):
                DxlClientConfig.create_dxl_config_from_file("mock_file.cfg")

    @parameterized.expand([
        (CONFIG_DATA_NO_BROKERS_SECTION,),
        (CONFIG_DATA_NO_BROKERS_OPTION,),
    ])
    def test_missing_brokers_doesnt_raise_exceptions(self, read_data):
        with patch.object(__builtin__, 'open', return_value=io.BytesIO(dedent(read_data))):
            client_config = DxlClientConfig.create_dxl_config_from_file("mock_file.cfg")
            self.assertEqual(len(client_config.brokers), 0)


class DxlClientTest(unittest.TestCase):
    def setUp(self):
        self.config = DxlClientConfig(broker_ca_bundle=get_ca_bundle_pem(),
                                      cert_file=get_cert_file_pem(),
                                      private_key=get_dxl_private_key(),
                                      brokers=[])

        mqtt_client_patch = patch('paho.mqtt.client.Client')
        mqtt_client_patch.start()

        self.client = DxlClient(self.config)
        self.client._request_manager.wait_for_response = Mock(return_value=Response(request=None))

        self.test_channel = '/test/channel'

    def tearDown(self):
        patch.stopall()

    def test_client_raises_exception_on_connect_when_already_connecting(self):
        self.client._client.connect.side_effect = Exception("An exception!")

        class MyThread(threading.Thread):
            def __init__(self, client):
                super(MyThread, self).__init__()
                self._client = client

            def run(self):
                self._client.connect()

        t = MyThread(self.client)
        t.setDaemon(True)
        t.start()
        time.sleep(2)

        self.assertEqual(self.client.connected, False)
        with self.assertRaises(DxlException):
            self.client.connect()
            # self.client.disconnect()

    def test_client_raises_exception_on_connect_when_already_connected(self):
        self.client._client.connect.side_effect = Exception("An exception!")
        self.client._connected = Mock(return_value=True)
        with self.assertRaises(DxlException):
            self.client.connect()
            # self.client.disconnect()

    # The following test is too slow
    def test_client_disconnect_doesnt_raises_exception_on_disconnect_when_disconnected(self):
        self.assertEqual(self.client.connected, False)
        self.client.disconnect()
        self.client.disconnect()

    @parameterized.expand([
        # (connect + retries) * 2 = connect_count
        (0, 2),
        (1, 4),
        (2, 6),
    ])
    def test_client_retries_defines_how_many_times_the_client_retries_connection(self, retries, connect_count):
        # Client wont' connect ;)
        self.client._client.connect = Mock(side_effect=Exception('Could not connect'))
        # No delay between retries (faster unit tests)
        self.client.config.reconnect_delay = 0
        self.client._wait_for_policy_delay = 0

        broker = Broker(host_name='localhost')
        broker._parse(UuidGenerator.generate_id_as_string() + ";9999;localhost;127.0.0.1")

        self.client.config.brokers = [broker]
        self.client.config.connect_retries = retries

        with self.assertRaises(DxlException):
            self.client.connect()
        self.assertEqual(self.client._client.connect.call_count, connect_count)
        # self.client.disconnect()

    def test_client_subscribe_adds_subscription_when_not_connected(self):
        self.client._client.subscribe = Mock(return_value=None)
        self.assertFalse(self.client.connected)

        self.client.subscribe(self.test_channel)
        self.assertTrue(self.test_channel in self.client.subscriptions)
        self.assertEqual(self.client._client.subscribe.call_count, 0)

    def test_client_unsubscribe_removes_subscription_when_not_connected(self):
        self.client._client.unsubscribe = Mock(return_value=None)
        self.assertFalse(self.client.connected)
        # Add subscription
        self.client.subscribe(self.test_channel)
        self.assertTrue(self.test_channel in self.client.subscriptions)
        # Remove subscription
        self.client.unsubscribe(self.test_channel)
        self.assertFalse(self.test_channel in self.client.subscriptions)

    def test_client_subscribe_doesnt_add_twice_same_channel(self):
        # Mock client.subscribe and is_connected
        self.client._client.subscribe = Mock(return_value=None)
        self.client._connected = Mock(return_value=True)

        # We always have the default (myself) channel
        self.assertEqual(len(self.client.subscriptions), 1)
        self.client.subscribe(self.test_channel)
        self.assertEqual(len(self.client.subscriptions), 2)
        self.client.subscribe(self.test_channel)
        self.assertEqual(len(self.client.subscriptions), 2)
        self.assertEqual(self.client._client.subscribe.call_count, 1)

    def test_client_handle_message_with_event_calls_event_callback(self):
        event_callback = EventCallback()
        event_callback.on_event = Mock()
        self.client.add_event_callback(self.test_channel, event_callback)
        # Create and process Event
        evt = Event(destination_topic=self.test_channel)._to_bytes()
        self.client._handle_message(self.test_channel, evt)
        # Check that callback was called
        self.assertEqual(event_callback.on_event.call_count, 1)

    def test_client_handle_message_with_request_calls_request_callback(self):
        req_callback = RequestCallback()
        req_callback.on_request = Mock()
        self.client.add_request_callback(self.test_channel, req_callback)
        # Create and process Request
        req = Request(destination_topic=self.test_channel)._to_bytes()
        self.client._handle_message(self.test_channel, req)
        # Check that callback was called
        self.assertEqual(req_callback.on_request.call_count, 1)

    def test_client_handle_message_with_response_calls_response_callback(self):
        callback = ResponseCallback()
        callback.on_response = Mock()
        self.client.add_response_callback(self.test_channel, callback)
        # Create and process Response
        msg = Response(request=None)._to_bytes()
        self.client._handle_message(self.test_channel, msg)
        # Check that callback was called
        self.assertEqual(callback.on_response.call_count, 1)

    def test_client_send_event_publishes_message_to_dxl_fabric(self):
        self.client._client.publish = Mock(return_value=None)
        # Create and process Request
        msg = Event(destination_topic="")
        self.client.send_event(msg)
        # Check that callback was called
        self.assertEqual(self.client._client.publish.call_count, 1)

    def test_client_send_request_publishes_message_to_dxl_fabric(self):
        self.client._client.publish = Mock(return_value=None)
        # Create and process Request
        msg = Request(destination_topic="")
        self.client._send_request(msg)
        # Check that callback was called
        self.assertEqual(self.client._client.publish.call_count, 1)

    def test_client_send_response_publishes_message_to_dxl_fabric(self):
        self.client._client.publish = Mock(return_value=None)
        # Create and process Request
        msg = Response(request=None)
        self.client.send_response(msg)
        # Check that callback was called
        self.assertEqual(self.client._client.publish.call_count, 1)

    def test_client_handles_error_response_and_fire_response_handler(self):
        self.client._fire_response = Mock(return_value=None)
        # Create and process Request
        msg = ErrorResponse(request=None, error_code=666, error_message="test message")
        payload = msg._to_bytes()
        # Handle error response message
        self.client._handle_message(self.test_channel, payload)
        # Check that message response was properly delivered to handler
        self.assertEqual(self.client._fire_response.call_count, 1)

    """
    Service unit tests
    """

    def test_client_register_service_subscribes_client_to_channel(self):
        channel1 = '/mcafee/service/unittest/one'
        channel2 = '/mcafee/service/unittest/two'
        # Create dummy service
        service_info = dxlclient.service.ServiceRegistrationInfo(
            service_type='/mcafee/service/unittest', client=self.client)
        service_info.add_topic(channel1, RequestCallback())
        service_info.add_topic(channel2, RequestCallback())

        # Register service in client
        self.client.register_service_async(service_info)
        # Check subscribed channels
        subscriptions = self.client.subscriptions
        assert channel1 in subscriptions, "Client wasn't subscribed to service channel"
        assert channel2 in subscriptions, "Client wasn't subscribed to service channel"

    def test_client_wont_register_the_same_service_twice(self):
        service_info = dxlclient.service.ServiceRegistrationInfo(
            service_type='/mcafee/service/unittest', client=self.client)

        # Register service in client
        self.client.register_service_async(service_info)
        with self.assertRaises(dxlclient.DxlException):
            # Re-register service
            self.client.register_service_async(service_info)

    def test_client_register_service_sends_register_request_to_broker(self):
        service_info = dxlclient.service.ServiceRegistrationInfo(
            service_type='/mcafee/service/unittest', client=self.client)

        self.client._send_request = Mock(return_value=True)
        self.client._connected = Mock(return_value=True)

        # Register service in client
        self.client.register_service_async(service_info)
        time.sleep(2)
        # Check that method has been called
        self.assertTrue(self.client._send_request.called)

    def test_client_register_service_unsubscribes_client_to_channel(self):
        channel1 = '/mcafee/service/unittest/one'
        channel2 = '/mcafee/service/unittest/two'
        # Create dummy service
        service_info = dxlclient.service.ServiceRegistrationInfo(
            service_type='/mcafee/service/unittest', client=self.client)
        service_info.add_topic(channel1, RequestCallback())
        service_info.add_topic(channel2, RequestCallback())

        # Register service in client
        self.client.register_service_async(service_info)
        # Check subscribed channels
        subscriptions = self.client.subscriptions
        assert channel1 in subscriptions, "Client wasn't subscribed to service channel"
        assert channel2 in subscriptions, "Client wasn't subscribed to service channel"

        self.client.unregister_service_async(service_info)
        subscriptions = self.client.subscriptions
        assert channel1 not in subscriptions, "Client wasn't unsubscribed to service channel"
        assert channel2 not in subscriptions, "Client wasn't unsubscribed to service channel"

    def test_client_register_service_unsuscribes_from_channel_by_guid(self):
        channel1 = '/mcafee/service/unittest/one'
        channel2 = '/mcafee/service/unittest/two'

        # Create dummy service
        service_info = dxlclient.service.ServiceRegistrationInfo(
            service_type='/mcafee/service/unittest', client=self.client)
        service_info.add_topic(channel1, RequestCallback())
        service_info.add_topic(channel2, RequestCallback())

        # Create same dummy service - different object
        service_info2 = service_info = dxlclient.service.ServiceRegistrationInfo(
            service_type='/mcafee/service/unittest', client=self.client)
        service_info._service_id = service_info.service_id
        service_info.add_topic(channel1, RequestCallback())
        service_info.add_topic(channel2, RequestCallback())

        # Register service in client
        self.client.register_service_async(service_info)

        # Check subscribed channels
        subscriptions = self.client.subscriptions
        assert channel1 in subscriptions, "Client wasn't subscribed to service channel"
        assert channel2 in subscriptions, "Client wasn't subscribed to service channel"

        self.client.unregister_service_async(service_info2)
        subscriptions = self.client.subscriptions
        assert channel1 not in subscriptions, "Client wasn't unsubscribed to service channel"
        assert channel2 not in subscriptions, "Client wasn't unsubscribed to service channel"


@attr('system')
class DxlClientSystemClientTest(BaseClientTest):

    def test_client_connects_to_broker_and_sets_current_broker(self):

        with self.create_client() as client:
            client.connect()
            broker_id = "unique_broker_id_1"

            self.assertTrue(client.connected)
            self.assertEqual(client.current_broker.unique_id, broker_id)

    def test_client_raises_exception_when_cannot_sync_connect_to_broker(self):

        with self.create_client() as client:
            broker = Broker("localhost", UuidGenerator.generate_id_as_string(), "127.0.0.1")
            client._config.brokers = [broker]

            with self.assertRaises(DxlException):
                client.connect()

    def test_client_receives_event_on_topic_only_after_subscribe(self):
        """
        The idea of this test is to send an event to a topic which we are not
        subscribed, so we shouldn't be notified. Then, we subscribe to that
        topic and send a new event, we should get that last one.
        """
        with self.create_client() as client:
            test_topic = '/test/whatever/' + client.config._client_id
            client.connect()
            time.sleep(2)
            self.assertTrue(client.connected)

            # Set request callback (use mock to easily check when it was called)
            ecallback = EventCallback()
            ecallback.on_event = Mock()
            client.add_event_callback(test_topic, ecallback, False)

            # Send event thru dxl fabric to a topic which we are *not* subscribed
            msg = Event(destination_topic=test_topic)
            client.send_event(msg)

            time.sleep(1)
            # We haven't been notified
            self.assertEqual(ecallback.on_event.call_count, 0)

            # Subscribe to topic
            client.subscribe(test_topic)
            time.sleep(1)

            # Send event thru dxl fabric again to that topic
            msg = Event(destination_topic=test_topic)
            client.send_event(msg)

            time.sleep(1)
            # Now we should have been notified of the event
            self.assertEqual(ecallback.on_event.call_count, 1)

    def test_client_receives_error_response_on_request_to_unknown_service(self):
        """
        The idea of this test is to send a sync request to an unknown service
        and get a "unable to locate service" error response.
        """
        with self.create_client() as client:
            test_topic = '/test/doesntexists/' + client.config._client_id
            client.connect()
            time.sleep(2)
            self.assertTrue(client.connected)

            # Send request thru dxl fabric to a service which doesn't exists
            msg = Request(destination_topic=test_topic)
            msg.service_id = UuidGenerator.generate_id_as_string()
            response = client.sync_request(msg, 1)

            # Check that we have an error response for our request
            self.assertTrue(isinstance(response, ErrorResponse))
            self.assertEqual(response.service_id, msg.service_id)


if __name__ == '__main__':
    unittest.main()
