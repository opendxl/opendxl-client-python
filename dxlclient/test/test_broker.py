# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2014 McAfee Inc. - All Rights Reserved.
################################################################################

# Run with python -m unittest dxlclient.test.test_broker

import unittest
import socket
from mock import patch, ANY
from nose.tools import raises

from dxlclient import Broker
from dxlclient.exceptions import MalformedBrokerUriException


class BrokerTest(unittest.TestCase):
    def setUp(self):
        self.socket_mock = patch('socket.socket', autospec=True).start()
        self.connection_mock = patch('socket.create_connection').start()
        self.connection_mock.return_value = self.socket_mock
        self.broker = Broker(host_name='localhost')

    def tearDown(self):
        patch.stopall()

    @raises(MalformedBrokerUriException)
    def test_parse_invalid_port(self):
        self.broker._parse("a ; b; [c] ")

    @raises(MalformedBrokerUriException)
    def test_parse_missing_hostname(self):
        self.broker._parse("a ; b;")

    @raises(MalformedBrokerUriException)
    def test_parse_port_out_of_range(self):
        self.broker._parse("a ; 65536; [c] ")

    def test_parse_valid_without_ip_address(self):
        self.broker._parse("a ; 8883; [c] ")
        self.assertTrue(self.broker.unique_id == "a")
        self.assertTrue(self.broker.port == 8883)
        self.assertTrue(self.broker.host_name == "c")

    @raises(MalformedBrokerUriException)
    def test_parse_valid_with_invalid_ip_address(self):
        self.broker._parse("a ; 8883; [c];[d] ")

    def test_parse_valid_with_iPv4_address(self):
        self.broker._parse("a ; 8883; [c];10.0.0.1 ")
        self.assertTrue(self.broker.unique_id == "a")
        self.assertTrue(self.broker.port == 8883)
        self.assertTrue(self.broker.host_name == "c")
        self.assertTrue(self.broker.ip_address == "10.0.0.1")

    def test_parse_valid_with_iPv6_address(self):
        self.broker._parse("a ; 8883; [c];[::1] ")
        self.assertTrue(self.broker.unique_id == "a")
        self.assertTrue(self.broker.port == 8883)
        self.assertTrue(self.broker.host_name == "c")
        self.assertTrue(self.broker.ip_address == "::1")

    def test_attributes(self):
        self.assertEqual(self.broker.unique_id, "")
        self.assertEqual(self.broker.host_name, "localhost")
        self.assertEqual(self.broker.ip_address, None)
        self.assertEqual(self.broker.port, 8883)
        self.assertEqual(self.broker._response_from_ip_address, None)
        self.assertEqual(self.broker._response_time, None)

    def test_connect_tries_first_using_hostname(self):
        self.broker._parse("broker_guid;8883;broker.fake.com;1.2.3.4")
        self.broker._connect_to_broker()
        self.assertEqual(self.broker._response_from_ip_address, False)
        self.assertIsNotNone(self.broker._response_time)
        self.connection_mock.assert_called_with(('broker.fake.com', 8883), timeout=ANY)

    def test_connect_uses_ip_address_when_connect_to_hostname_fails(self):
        self.connection_mock.side_effect = [socket.error, self.socket_mock]
        self.broker._parse("broker_guid;8883;broker.fake.com;1.2.3.4")
        self.broker._connect_to_broker()
        self.assertEquals(self.connection_mock.call_count, 2)
        self.assertEqual(self.broker._response_from_ip_address, True)
        self.assertIsNotNone(self.broker._response_time)
        self.connection_mock.assert_called_with(('1.2.3.4', 8883), timeout=ANY)

    def test_close_once(self):
        self.broker._parse("broker_guid;8883;broker.fake.com;1.2.3.4")
        self.broker._connect_to_broker()
        self.assertEquals(self.socket_mock.close.call_count, 1)

    def test_close_once_when_errors(self):
        self.connection_mock.side_effect = [socket.error, self.socket_mock]
        self.broker._parse("broker_guid;8883;broker.fake.com;1.2.3.4")
        self.broker._connect_to_broker()
        self.assertEquals(self.socket_mock.close.call_count, 1)
