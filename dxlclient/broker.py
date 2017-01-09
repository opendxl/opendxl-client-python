# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2017 McAfee Inc. - All Rights Reserved.
################################################################################

import re
import socket
import datetime
import logging

from dxlclient import _BaseObject
from dxlclient.exceptions import MalformedBrokerUriException
from dxlclient._server_name_helper import ServerNameHelper

logger = logging.getLogger(__name__)


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

    def __del__(self):
        """Destructor"""
        super(Broker, self).__del__()

    @property
    def unique_id(self):
        """
        A unique identifier for the broker, used to identify the broker in log messages, etc.
        """
        return self._unique_id

    @unique_id.setter
    def unique_id(self, id):
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
        # Remove brackets around IPv6 address
        host = re.sub(r"[\[\]]", "", host_name)
        if not ServerNameHelper.is_valid_hostname_or_ip_address(host):
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
        ip = ip_address
        if ip:
            # Remove brackets around IPv6 address
            ip = re.sub(r"[\[\]]", "", ip_address)
            if not ServerNameHelper.is_valid_ip_address(ip):
                raise MalformedBrokerUriException("Invalid IP address")
        self._ip_address = ip

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
        elements = host_name.split(":")
        if len(elements) == 2:
            host_name = elements[0]
            port = elements[1]
        broker.host_name = host_name
        broker.port = port

        if protocol and not protocol.lower() == Broker._SSL_PROTOCOL.lower():
            raise MalformedBrokerUriException("Unknown protocol: " + protocol)

        return broker

    def _parse(self, broker_string):
        """
        Constructs a Broker object for the specified broker string
        in the format [UniqueId];[Port];[HostName];[IpAddress]

        :param broker_string: The broker definition as a string
        :return: None
        """
        elements = [a.strip() for a in broker_string.split(self._FIELD_SEPARATOR)]
        len_elems = len(elements)
        attrs = {}
        if len_elems < 2:
            raise MalformedBrokerUriException("Missing elements")
        else:
            if Broker._is_port_number(elements[0]):
                attrs['port'] = elements[0]
                attrs['hostname'] = elements[1]
                if len_elems > 2:
                    attrs['ip_address'] = elements[2]
            else:
                attrs['unique_id'] = elements[0]
                attrs['port'] = elements[1]
                attrs['hostname'] = elements[2]
                if len_elems > 3:
                    attrs['ip_address'] = elements[3]
        # Sets broker attributes from the dictionary generated.
        self._set_attributes(attrs)

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
        except socket.error, msg:
            if self._ip_address is not None:
                try:
                    start = datetime.datetime.now()
                    broker_s = socket.create_connection((self._ip_address, self._port), timeout=1.0)
                    end = datetime.datetime.now()
                    self._response_from_ip_address = True
                    self._response_time = (end - start).total_seconds()
                except socket.error, msg:
                    logger.error("Socket could not be created. Error Code : " + str(msg.errno) + " Message " + str(msg.message))
            else:
                logger.error("Socket could not be created. Error Code : " + str(msg.errno) + " Message " + str(msg.message))
        finally:
            if broker_s is not None:
                broker_s.close()

    def _set_attributes(self, attrs):
        """
        Sets broker attributes from the input dictionary with format:
            {'unique_id': <UNIQUE_ID>, 'port': <PORT>, 'hostname': <HOSTNAME>, 'ip_address': <IP>}
            Required keys: 'port' and 'hostname'.
        Pre: 'port' in attrs and 'hostname' in attrs
        :param attrs: input dictionary with broker attributes.
        """
        # Unique ID : optional
        if 'unique_id' in attrs:
            self.unique_id = attrs['unique_id']
        else:
            self.unique_id = None
        # Port : required
        self.port = attrs['port']
        # Hostname : required
        self.host_name = attrs['hostname']
        # IP address : optional
        if 'ip_address' in attrs:
            self.ip_address = attrs['ip_address']
        else:
            self.ip_address = None

    @staticmethod
    def _is_port_number(input):
        """
        Indicates if the input is a valid port number.
        :param input: Port number to check.
        :return: True if the input is a valid port number, false otherwise.
        """
        res = True
        try:
            port = int(input)
            if port < 1 or port > 65535:
                res = False
        except Exception, e:
            res = False
        return res
