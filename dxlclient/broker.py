# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
################################################################################

"""
Contains the :class:`Broker` class, which represents a DXL message broker.
"""

from __future__ import absolute_import
import re
import socket
import datetime
import logging

from dxlclient import _BaseObject
from dxlclient.exceptions import MalformedBrokerUriException
from dxlclient._uuid_generator import UuidGenerator

logger = logging.getLogger(__name__)


# pylint: disable=attribute-defined-outside-init, too-many-instance-attributes
class Broker(_BaseObject):
    """
    The class :class:`Broker` represents a DXL message broker.

    Instances of this class are created for the purpose of connecting to the DXL fabric.

    There are several ways to create :class:`Broker` instances:

    - Invoking the :class:`Broker` constructor directly
    - Passing a properly formatted string to the static :func:`parse` method of :class:`Broker`
    - When creating a :class:`dxlclient.client_config.DxlClientConfig` object
      via the :func:`dxlclient.client_config.DxlClientConfig.create_dxl_config_from_file` static method

    """
    _FIELD_SEPARATOR = ';'
    """The field separator used by the e :func:`dxlclient.broker.Broker.parse` method"""
    _SSL_PROTOCOL = "ssl"
    """The SSL protocol identifier"""
    _SSL_PORT = 8883
    """The standard TLS port"""

    def __init__(self, host_name, unique_id=None, ip_address=None, port=_SSL_PORT):
        """
        Constructor parameters:

        :param host_name: The host name or IP address of the broker (required)
        :param unique_id: A unique identifier for the broker, used to identify the broker in log messages, etc.
            (optional)
        :param ip_address: A valid IP address for the broker. This allows for both the host name and IP address
            to be used when connecting to the broker (optional).
        :param port: The port of the broker (defaults to 8883)
        """
        super(Broker, self).__init__()

        # The unique ID of the Broker
        self.unique_id = unique_id
        # The hostName or IP address of the broker
        self.host_name = host_name
        # The IP address of the broker (optional)
        self.ip_address = ip_address
        # The TCP port of the broker
        self.port = port
        # The broker response came from the secondary test using the IP address
        self._response_from_ip_address = None
        # The broker response time in nanoseconds, or None if no response or not tested
        self._response_time = None

    @property
    def unique_id(self):
        """
        A unique identifier for the broker, used to identify the broker in log messages, etc.
        """
        return self._unique_id

    @unique_id.setter
    def unique_id(self, id): # pylint: disable=invalid-name, redefined-builtin
        if id:
            self._unique_id = id
        else:
            self._unique_id = ""

    @property
    def host_name(self):
        """
        The host name or IP address of the broker
        """
        return self._host_name

    @host_name.setter
    def host_name(self, host_name):
        if host_name:
            # Remove brackets around IPv6 address
            host = re.sub(r"[\[\]]", "", host_name)
        else:
            raise MalformedBrokerUriException("Invalid host name")
        self._host_name = host

    @property
    def ip_address(self):
        """
        A valid IP address for the broker. This allows for both the host name and IP address
        to be used when connecting to the broker
        """
        return self._ip_address

    @ip_address.setter
    def ip_address(self, ip_address):
        if ip_address:
            # Remove brackets around IPv6 address
            ip_address = re.sub(r"[\[\]]", "", ip_address)
        self._ip_address = ip_address

    @property
    def port(self):
        """
        The port of the broker
        """
        return self._port

    @port.setter
    def port(self, port):
        if Broker._is_port_number(port):
            self._port = int(port)
        else:
            raise MalformedBrokerUriException("Invalid port")

    def to_string(self):
        """Returns a string representation of the broker for the purposes of logging, etc."""
        ret = "{"
        if self.unique_id:
            ret += "Unique id: " + self.unique_id + ", "
        ret += "Host name: " + self.host_name
        if self.ip_address:
            ret += ", IP address: " + self.ip_address
        ret += ", Port: " + str(self.port)
        ret += "}"
        return ret

    @staticmethod
    def parse(broker_url):
        """
        Returns a broker instance corresponding to the specified broker URL of the form:

        ``[ssl://]<hostname>[:port]``

        Valid URLs include:

        - ``ssl://mybroker:8883``
        - ``ssl://mybroker``
        - ``mybroker:8883``
        - ``mybroker``

        If the port is omitted it will be defaulted to 8883.

        :param broker_url: A valid broker URL
        :return: A broker corresponding to the specified broker URL
        """
        broker = Broker(host_name='none')
        elements = broker_url.split("://")
        host_name = broker_url
        protocol = Broker._SSL_PROTOCOL
        port = Broker._SSL_PORT
        if len(elements) == 2:
            protocol = elements[0]
            host_name = elements[1]
        if host_name[-1] != ']':
            host_name_left, _, host_name_right = host_name.rpartition(":")
            if host_name_left:
                host_name = host_name_left
                port = host_name_right
        broker.host_name = host_name
        broker.port = port
        broker.unique_id = UuidGenerator.generate_id_as_string()

        if protocol and protocol.lower() != Broker._SSL_PROTOCOL.lower():
            raise MalformedBrokerUriException("Unknown protocol: " + protocol)

        return broker

    @staticmethod
    def _get_array_element_or_none(arr, arr_position):
        return arr[arr_position] if len(arr) > arr_position else None

    def _parse(self, broker_string):
        """
        Constructs a Broker object for the specified broker string
        in the format [UniqueId];[Port];[HostName];[IpAddress]

        :param broker_string: The broker definition as a string
        :return: None
        """
        elements = [a.strip() for a in broker_string.split(self._FIELD_SEPARATOR)]

        if len(elements) < 2:
            raise MalformedBrokerUriException("Missing elements")
        else:
            if Broker._is_port_number(elements[0]):
                self.unique_id = None
                self.port = elements[0]
                self.host_name = elements[1]
                self.ip_address = self._get_array_element_or_none(elements, 2)
            else:
                self.unique_id = elements[0]
                self.port = elements[1]
                self.host_name = self._get_array_element_or_none(elements, 2)
                self.ip_address = self._get_array_element_or_none(elements, 3)

    def _to_broker_string(self):
        """
        Dumps the content of the current Broker instance into a broker string
        in the format {[UniqueID];}[Port};[HostName]{;[IpAddress]}. Note that
        the UniqueId and/or IpAddress fields will be absent from the string
        output when not set on the Broker instance.

        :return: the broker string
        :rtype: str
        """
        return "{}{}{}{}{}".format(
            "{}{}".format(self.unique_id, self._FIELD_SEPARATOR)
            if self.unique_id else "",
            self._port,
            self._FIELD_SEPARATOR,
            self._host_name,
            "{}{}".format(self._FIELD_SEPARATOR, self._ip_address)
            if self.ip_address else "")

    def _connect_to_broker(self):
        """
        Attempts to connect to a broker.
        Upon success will set the response time and whether the response
        came from the IP address versus the hostname.
        :return: None
        """
        broker_s = None
        try:
            start = datetime.datetime.now()
            broker_s = socket.create_connection((self._host_name, self._port), timeout=1.0)
            end = datetime.datetime.now()
            self._response_from_ip_address = False
            self._response_time = (end - start).total_seconds()
        except socket.error as msg:
            if self._ip_address:
                try:
                    start = datetime.datetime.now()
                    broker_s = socket.create_connection((self._ip_address, self._port), timeout=1.0)
                    end = datetime.datetime.now()
                    self._response_from_ip_address = True
                    self._response_time = (end - start).total_seconds()
                except socket.error as msg:
                    logger.error(
                        "Socket could not be created. Error Code: %s. Message: %s.",
                        msg.errno, msg)
            else:
                logger.error(
                    "Socket could not be created. Error Code: %s. Message: %s.",
                    msg.errno, msg)
        finally:
            if broker_s is not None:
                broker_s.close()

    @staticmethod
    def _is_port_number(port):
        """
        Indicates if the input is a valid port number.
        :param port: Port number to check.
        :return: True if the input is a valid port number, false otherwise.
        """
        res = True
        try:
            port_int = int(port)
            if port_int < 1 or port_int > 65535:
                res = False
        except (TypeError, ValueError):
            res = False
        return res
