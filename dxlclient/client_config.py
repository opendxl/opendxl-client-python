# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
################################################################################

"""
Contains the :class:`DxlClientConfig` class, which holds the information
necessary to connect a :class:`dxlclient.client.DxlClient` to the DXL fabric.
"""

from __future__ import absolute_import
from collections import OrderedDict
import logging
from os import path
import threading
import socket
from configobj import ConfigObj

from dxlclient import _BaseObject, DxlUtils
from dxlclient.broker import Broker
from dxlclient._uuid_generator import UuidGenerator
from dxlclient.exceptions import BrokerListError, InvalidProxyConfigurationError

from ._compat import Queue

################################################################################
#
# Static functions
#
################################################################################
logger = logging.getLogger(__name__)


def _get_brokers_from_list(broker_list):
    """
    Helper function that generates a broker list from a dictionary containing brokers in this format
    {
        "{guid}": "{guid};port;broker-name;broker_ip",
        "{guid-2}": "{guid-2};port;broker-2-name;broker-2-ip",
        ...
    }
    :param broker_list: Dictionary with brokers info
    :return: list of broker objects
    """
    brokers = None
    if broker_list is not None:
        brokers = []
        for _, value in broker_list.items():
            # Set hostname to avoid validation error, will be overridden by parse
            broker = Broker(host_name='none')
            broker._parse(value)
            brokers.append(broker)
    return brokers


def _get_brokers(broker_list_json):
    """
    From a json object creates a broker list

    :param broker_list_json: json object containing a dictionary with a BrokerList tag
    :return: list of broker objects
    """
    try:
        return _get_brokers_from_list(broker_list_json)
    except Exception as broker_error:
        raise BrokerListError("Broker list is not a valid JSON: " + str(broker_error))


def _validate_proxy_address(address):
    """
    Validates HTTP proxy address
    :param address: HTTP proxy address
    """
    try:
        if not (socket.gethostbyname(address) == address or socket.gethostbyname(address) != address):
            raise socket.gaierror
    except socket.gaierror as proxy_address_error:
        raise InvalidProxyConfigurationError("Proxy address is not valid: " + str(proxy_address_error))


def _validate_proxy_port(port):
    """
    Validates HTTP proxy port
    :param port: HTTP proxy port
    """
    try:
        if not 1 <= int(port) <= 65535:
            raise ValueError
    except ValueError as proxy_port_error:
        raise InvalidProxyConfigurationError("Proxy port is not valid. Port number must be an integer "
                                             "between 1-65535: " + str(proxy_port_error))

################################################################################
#
# DxlClientConfig
#
################################################################################


class DxlClientConfig(_BaseObject):
    """
    The Data Exchange Layer (DXL) client configuration contains the information necessary to connect
    a :class:`dxlclient.client.DxlClient` to the DXL fabric.

    The configuration includes the required PKI information (client certificate, client private key,
    broker CA certificates) and the set of DXL message brokers that are available to connect to on the fabric.

    The following sample shows creating a client configuration, instantiating a DXL client, and connecting
    to the fabric:

    .. code-block:: python

        from dxlclient.broker import Broker
        from dxlclient.client import DxlClient
        from dxlclient.client_config import DxlClientConfig

        # Create the client configuration
        config = DxlClientConfig(
            broker_ca_bundle="c:\\\\certs\\\\brokercerts.crt",
            cert_file="c:\\\\certs\\\\client.crt",
            private_key="c:\\\\certs\\\\client.key",
            brokers=[Broker.parse("ssl://192.168.189.12")])

        # Create the DXL client
        with DxlClient(config) as dxl_client:

            # Connect to the fabric
            dxl_client.connect()
    """

    # Config file keys
    _CERTS_SECTION = u"Certs"
    _BROKER_CERT_CHAIN_SETTING = u"BrokerCertChain"
    _CERT_FILE_SETTING = u"CertFile"
    _PRIVATE_KEY_SETTING = u"PrivateKey"

    _BROKERS_SECTION = u"Brokers"
    _BROKERS_WEBSOCKETS_SECTION = u"BrokersWebSockets"

    _GENERAL_SECTION = u"General"
    _CLIENT_ID_SETTING = u"ClientId"
    _USE_WEBSOCKETS_SETTING = u"useWebSockets"

    # HTTP Proxy Section
    _PROXY_SECTION = u"Proxy"
    # HTTP Proxy Settings
    _PROXY_ADDRESS_SETTING = u"Address"
    _PROXY_PORT_SETTING = u"Port"
    _PROXY_USERNAME_SETTING = u"User"
    _PROXY_PASSWORD_SETTING = u"Password"

    _REQUIRED = True
    _NOT_REQUIRED = False

    _SETTINGS = (
        (_GENERAL_SECTION,
         ((_CLIENT_ID_SETTING, "Client Id", _NOT_REQUIRED),
          (_USE_WEBSOCKETS_SETTING, "Use WebSockets", _NOT_REQUIRED)),
         _NOT_REQUIRED),
        (_CERTS_SECTION,
         ((_BROKER_CERT_CHAIN_SETTING, "Broker CA bundle", _REQUIRED),
          (_CERT_FILE_SETTING, "Certificate file", _REQUIRED),
          (_PRIVATE_KEY_SETTING, "Private key file", _REQUIRED)),
         _REQUIRED),
        (_BROKERS_SECTION, (), _REQUIRED),
        (_BROKERS_WEBSOCKETS_SECTION, (), _REQUIRED),
        (_PROXY_SECTION,
         ((_PROXY_ADDRESS_SETTING, "Address", _NOT_REQUIRED),
          (_PROXY_PORT_SETTING, "Port", _NOT_REQUIRED),
          (_PROXY_USERNAME_SETTING, "User", _NOT_REQUIRED),
          (_PROXY_PASSWORD_SETTING, "Password", _NOT_REQUIRED)),
         _NOT_REQUIRED))

    # The default number of times to retry during connect, default -1 (infinite)
    _DEFAULT_CONNECT_RETRIES = -1
    # The default keep alive interval (in seconds); client pings broker at interval
    # 30 minutes by default
    _DEFAULT_MQTT_KEEP_ALIVE_INTERVAL = 30 * 60
    # The default reconnect back off multiplier
    _DEFAULT_RECONNECT_BACK_OFF_MULTIPLIER = 2
    # The default reconnect delay (in seconds)
    _DEFAULT_RECONNECT_DELAY = 1
    # The default maximum reconnect delay, defaults to 1 minute
    _DEFAULT_RECONNECT_DELAY_MAX = 60
    # The default reconnect delay random multiplier, defaults to 25 percent
    _DEFAULT_RECONNECT_DELAY_RANDOM = 0.25
    # Whether to attempt to reconnect when disconnected
    _DEFAULT_RECONNECT_WHEN_DISCONNECTED = True
    # Default proxy type is 3 i.e HTTP
    _DEFAULT_PROXY_TYPE = 3
    # Default proxy rdns setting is set to True
    _DEFAULT_PROXY_RDNS = True

    def __init__(self, broker_ca_bundle, cert_file, private_key, brokers, websocket_brokers=None, **proxy_args):
        """
        Constructor parameters:

        :param broker_ca_bundle: The file name of a bundle containing the broker CA certificates in PEM format
        :param cert_file: The file name of the client certificate in PEM format
        :param private_key: The file name of the client private key in PEM format
        :param brokers: A list of :class:`dxlclient.broker.Broker` objects representing brokers on the
            DXL fabric supporting standard MQTT connections. When invoking the
            :func:`dxlclient.client.DxlClient.connect` method, the :class:`dxlclient.client.DxlClient` will attempt to
            connect to the closest broker.
        :param websocket_brokers: A list of :class:`dxlclient.broker.Broker` objects representing brokers on the
            DXL fabric supporting DXL connections over WebSockets.
        :param proxy_args: Websocket proxy arguments
        """
        super(DxlClientConfig, self).__init__()

        self._config = ConfigObj()
        self._config_path = None
        DxlClientConfig._create_required_sections(self)

        # The filename of the CA bundle file in PEM format
        self.broker_ca_bundle = broker_ca_bundle
        # The filename of the client certificate in PEM format (must not have a password)
        self.cert_file = cert_file
        # The filename of the private key used to request the certificates
        self.private_key = private_key
        # The list of brokers
        self._brokers = brokers
        # The list of WebSocket brokers
        self._websocket_brokers = websocket_brokers
        # Whether to use WebSockets or regular MQTT over tcp
        self._use_websockets = False
        # Proxy settings
        self._proxy_type = None
        self._proxy_rdns = None
        self._proxy_addr = proxy_args.get("proxy_addr", None)
        self._proxy_port = proxy_args.get("proxy_port", None)
        self._proxy_username = proxy_args.get("proxy_username", None)
        self._proxy_password = proxy_args.get("proxy_password", None)

        # Common initialization which needs to be done whether an object is
        # created via :meth:`__init__` or :meth:`_init_from_config_file` is
        # done in :meth:`_init_common`. :meth:`_init_common` redefines values
        # for each of the attributes below.
        self._connect_retries = None
        self._keep_alive_interval = None
        self._reconnect_back_off_multiplier = None
        self._reconnect_delay = None
        self._reconnect_delay_max = None
        self._reconnect_delay_random = None
        self._reconnect_when_disconnected = None
        self._client_id = None
        self._queue = None
        self._incoming_message_queue_size = None
        self._incoming_message_thread_pool_size = None
        self._init_common()

    def _create_required_sections(self):
        """
        Create all of the sections in the configuration model which are
        required in order for the configuration to be valid.
        """
        for section in self._SETTINGS:
            section_name, _, section_required = section
            if section_required and section_name not in self._config:
                self._config[section_name] = {}
                # Add a blank line before new sections after the first one
                if len(self._config) > 1:
                    self._config.comments[section_name].insert(0, '')

    def _validate_required_content(self):
        """
        Validate that each of the required sections and settings are present
        in the configuration.

        :raise ValueError: if any of the required sections or settings are
            missing
        """
        for section in self._SETTINGS:
            section_name, settings, section_required = section
            if section_required:
                if section_name not in self._config or \
                        self._config[section_name] is None:
                    raise ValueError("{} not specified".format(section_name))
                for setting in settings:
                    setting_name, setting_description, setting_required = \
                        setting
                    if setting_required and \
                            (setting_name not in self._config[section_name] or
                             not self._config[section_name][setting_name]):
                        raise ValueError("{} not specified".format(
                            setting_description))

    def _init_common(self):
        """
        Common initialization which needs to be done whether an object is
        created via `__init__` or `_init_from_config_file` is done in this
        method.
        """
        self._validate_required_content()

        client_id = UuidGenerator.generate_id_as_string()

        # The number of times to retry during connect
        self._connect_retries = self._DEFAULT_CONNECT_RETRIES
        # The keep alive interval
        self._keep_alive_interval = self._DEFAULT_MQTT_KEEP_ALIVE_INTERVAL
        # The reconnect back off multiplier
        self._reconnect_back_off_multiplier = \
            self._DEFAULT_RECONNECT_BACK_OFF_MULTIPLIER
        # The reconnect delay (in seconds)
        self._reconnect_delay = self._DEFAULT_RECONNECT_DELAY
        # The maximum reconnect delay
        self._reconnect_delay_max = self._DEFAULT_RECONNECT_DELAY_MAX
        # The reconnect delay random
        self._reconnect_delay_random = self._DEFAULT_RECONNECT_DELAY_RANDOM
        # Whether to reconnect when disconnected
        self._reconnect_when_disconnected = \
            self._DEFAULT_RECONNECT_WHEN_DISCONNECTED

        # The unique identifier of the client
        self._client_id = client_id
        # Queue for getting the sorted broker list
        self._queue = None
        # The incoming message queue size
        self._incoming_message_queue_size = 1000
        # The incoming thread pool size
        self._incoming_message_thread_pool_size = 1
        # Default proxy settings for rdns and proxy type
        self._proxy_type = self._DEFAULT_PROXY_TYPE
        self._proxy_rdns = self._DEFAULT_PROXY_RDNS

    def _get_value_from_config(self, section_or_setting_name):
        """
        Get a value from the underlying configuration model.

        :param section_or_setting_name: name of either a section or a setting
            name whose value should be retrieved. The valid section and setting
            names derive from :const:`_SETTINGS`.
        :return: value for the section or setting, `None` if not found.
        """
        value = None
        for section in DxlClientConfig._SETTINGS:
            section_name, settings, _ = section
            if section_name == section_or_setting_name:
                value = self._config[section_name] \
                    if section_name in self._config else None
            for setting in settings:
                setting_name = setting[0]
                if setting_name == section_or_setting_name:
                    if section_name in self._config:
                        section_value = self._config[section_name]
                        value = section_value[setting_name] \
                            if setting_name in section_value else None
                    else:
                        value = None
                    break
            if value:
                break
        return value

    def _set_value_to_config(self, section_or_setting_name, value):
        """
        Set the supplied value into the configuration for the specified
        `section_or_setting_name.

        :param section_or_setting_name: name of either a section or a setting
            name whose value should be set. The valid section and setting
            names derive from :const:`_SETTINGS`.
        :raise ValueError: if the value to be set is not defined in
            :const:`_SETTINGS`.
        """
        value_was_set = False
        for section in DxlClientConfig._SETTINGS:
            section_name, settings, _ = section
            if section_name == section_or_setting_name:
                self._config[section_or_setting_name] = value
                value_was_set = True
                break
            for setting in settings:
                setting_name = setting[0]
                if setting_name == section_or_setting_name:
                    if section_name not in self._config:
                        self._config[section_name] = {}
                    self._config[section_name][section_or_setting_name] = value
                    value_was_set = True
                    break
            if value_was_set:
                break
        if not value_was_set:
            raise ValueError("Unrecognized setting could not be set: {}".
                             format(section_or_setting_name))

    @property
    def broker_ca_bundle(self):
        """
        The file name of a bundle containing the broker CA certificates in PEM
        format
        """
        return self._get_file_path(self._get_value_from_config(
            self._BROKER_CERT_CHAIN_SETTING))

    @broker_ca_bundle.setter
    def broker_ca_bundle(self, broker_ca_bundle):
        self._set_value_to_config(self._BROKER_CERT_CHAIN_SETTING,
                                  broker_ca_bundle)

    @property
    def cert_file(self):
        """
        The file name of the client certificate in PEM format
        """
        return self._get_file_path(self._get_value_from_config(
            self._CERT_FILE_SETTING))

    @cert_file.setter
    def cert_file(self, cert_file):
        self._set_value_to_config(self._CERT_FILE_SETTING, cert_file)

    @property
    def private_key(self):
        """
        The file name of the client private key in PEM format
        """
        return self._get_file_path(self._get_value_from_config(
            self._PRIVATE_KEY_SETTING))

    @private_key.setter
    def private_key(self, private_key):
        self._set_value_to_config(self._PRIVATE_KEY_SETTING, private_key)

    @property
    def brokers(self):
        """
        A list of :class:`dxlclient.broker.Broker` objects representing brokers on the
        DXL fabric. Brokers returned is dependent on the use_websockets flag. When invoking the
        :func:`dxlclient.client.DxlClient.connect` method, the :class:`dxlclient.client.DxlClient` will attempt to
        connect to the closest broker.
        """
        if self.use_websockets:
            return self.websocket_brokers
        return self._brokers

    @brokers.setter
    def brokers(self, brokers):
        self._brokers = brokers

    @property
    def websocket_brokers(self):
        """
        A list of :class:`dxlclient.broker.Broker` objects representing brokers on the
        DXL fabric supporting DXL connections over WebSockets.
        """
        return self._websocket_brokers

    @websocket_brokers.setter
    def websocket_brokers(self, websocket_brokers):
        self._websocket_brokers = websocket_brokers

    @property
    def use_websockets(self):
        """
        Whether or not the client will use WebSockets. If false MQTT over tcp will be used. If only WebSocket brokers
        are specified this will default to true.
        """
        return self._use_websockets

    @use_websockets.setter
    def use_websockets(self, use_websockets):
        self._use_websockets = use_websockets
        self._set_value_to_config(self._USE_WEBSOCKETS_SETTING, use_websockets)

    @property
    def proxy_addr(self):
        """
        Get proxy address
        """
        return self._proxy_addr

    @proxy_addr.setter
    def proxy_addr(self, proxy_addr):
        """
        Set proxy address
        :param proxy_addr: Proxy address
        """
        self._proxy_addr = proxy_addr

    @property
    def proxy_port(self):
        """
        Get proxy port
        """
        return self._proxy_port

    @proxy_port.setter
    def proxy_port(self, proxy_port):
        """
        Set Proxy Port
        :param proxy_port: Proxy Port
        """
        self._proxy_port = proxy_port

    @property
    def proxy_username(self):
        """
        Get proxy username
        """
        return self._proxy_username

    @proxy_username.setter
    def proxy_username(self, proxy_username):
        """
        Set Proxy Username
        :param proxy_username: Proxy username
        """
        self._proxy_username = proxy_username

    @property
    def proxy_password(self):
        """
        Get proxy password
        """
        return self._proxy_password

    @proxy_password.setter
    def proxy_password(self, proxy_password):
        """
        Set proxy username
        :param proxy_password: Proxy password
        """
        self._proxy_password = proxy_password

    @property
    def proxy_type(self):
        """
        Get Type of Proxy. Defaults to 3 (HTTP)
        """
        return self._proxy_type

    @proxy_type.setter
    def proxy_type(self, proxy_type):
        """
        Sets the proxy type
        :param proxy_type: Proxy Type
        """
        self._proxy_type = proxy_type

    @property
    def proxy_rdns(self):
        """
        Returns Proxy rdns enabled or not. Defaults to True
        """
        return self._proxy_rdns

    @proxy_rdns.setter
    def proxy_rdns(self, proxy_rdns):
        """
        Sets the Proxy rdns
        :param proxy_rdns: Proxy rdns
        """
        self._proxy_rdns = proxy_rdns

    @property
    def incoming_message_queue_size(self):
        """
        The queue size for incoming messages (will block when queue is full).

        Defaults to ``1000``
        """
        return self._incoming_message_queue_size

    @incoming_message_queue_size.setter
    def incoming_message_queue_size(self, incoming_message_queue_size):
        self._incoming_message_queue_size = incoming_message_queue_size

    @property
    def incoming_message_thread_pool_size(self):
        """
        The thread pool size for incoming messages

        Defaults to ``1``
        """
        return self._incoming_message_thread_pool_size

    @incoming_message_thread_pool_size.setter
    def incoming_message_thread_pool_size(self, incoming_message_thread_pool_size):
        self._incoming_message_thread_pool_size = incoming_message_thread_pool_size

    @property
    def connect_retries(self):
        """
        The maximum number of connection attempts for each :class:`dxlclient.broker.Broker`
        specified in the :class:`dxlclient.client_config.DxlClientConfig`

        A value of ``-1`` indicates that the client will continue to retry without limit until it
        establishes a connection
        """
        return self._connect_retries

    @connect_retries.setter
    def connect_retries(self, connect_retries):
        """
        Sets the number of retries to perform when connecting. A value of -1
        indicates retry forever.

        :param connect_retries: The number of retries. A value of -1 indicates
                                retry forever.
        """
        self._connect_retries = connect_retries

    @property
    def keep_alive_interval(self):
        """
        The maximum period in seconds between communications with a connected :class:`dxlclient.broker.Broker`.
        If no other messages are being exchanged, this controls the rate at which the client will send ping
        messages to the :class:`dxlclient.broker.Broker`.

        Defaults to ``1800`` seconds (30 minutes)
        """
        return self._keep_alive_interval

    @property
    def reconnect_back_off_multiplier(self):
        """
        Multiples the current reconnect delay by this value on subsequent connect retries. For example, a current
        delay of 3 seconds with a multiplier of 2 would result in the next retry attempt being in 6 seconds.

        Defaults to ``2``
        """
        return self._reconnect_back_off_multiplier

    @reconnect_back_off_multiplier.setter
    def reconnect_back_off_multiplier(self, reconnect_back_off_multiplier):
        self._reconnect_back_off_multiplier = reconnect_back_off_multiplier

    @keep_alive_interval.setter
    def keep_alive_interval(self, keep_alive_interval):
        self._keep_alive_interval = keep_alive_interval

    @property
    def reconnect_delay(self):
        """
        The initial delay between retry attempts in seconds. The delay increases ("backs off")
        as subsequent connection attempts are made.

        Defaults to ``1`` second
        """
        return self._reconnect_delay

    @reconnect_delay.setter
    def reconnect_delay(self, reconnect_delay):
        self._reconnect_delay = reconnect_delay

    @property
    def reconnect_delay_max(self):
        """
        The maximum delay between connection retry attempts in seconds

        Defaults to ``60`` seconds (1 minute)
        """
        return self._reconnect_delay_max

    @reconnect_delay_max.setter
    def reconnect_delay_max(self, reconnect_delay_max):
        self._reconnect_delay_max = reconnect_delay_max

    @property
    def reconnect_delay_random(self):
        """
        Get the randomness delay percentage (between 0.0 and 1.0).
        The default value is 0.25
        """
        return self._reconnect_delay_random

    @reconnect_delay_random.setter
    def reconnect_delay_random(self, reconnect_delay_random):
        """
        Sets a randomness delay percentage (between 0.0 and 1.0). When
        calculating the reconnect delay, this percentage indicates how much
        randomness there should be in the current delay. For example, if the
        current delay is 100ms, a value of .25 would mean that the actual delay
        would be between 100ms and 125ms.

        :param reconnect_delay_random: The randomness delay percentage (between 0.0 and 1.0).
        """
        self._reconnect_delay_random = reconnect_delay_random

    @property
    def reconnect_when_disconnected(self):
        """
        Whether the client will continuously attempt to reconnect to the fabric if it becomes disconnected

        Defaults to ``True``
        """
        return self._reconnect_when_disconnected

    @reconnect_when_disconnected.setter
    def reconnect_when_disconnected(self, reconnect):
        self._reconnect_when_disconnected = reconnect

    @staticmethod
    def _get_sorted_broker_list_worker(broker):
        """Returns a sorted list of the brokers in this config."""
        broker._connect_to_broker()

    def _get_http_proxy(self):
        """
        Returns the web socket http proxy as a dictionary if present in the config
        :return: HTTP Proxy arguments dictionary.(Can be empty)
        """
        proxy = {}
        proxy_addr = self.proxy_addr
        proxy_port = self.proxy_port
        if not self.use_websockets or proxy_addr is None or proxy_port is None:
            return proxy
        _validate_proxy_address(proxy_addr)
        _validate_proxy_port(proxy_port)
        proxy = {'proxy_password': self.proxy_password, 'proxy_port': int(proxy_port),
                 'proxy_addr': proxy_addr, 'proxy_username': self.proxy_username,
                 'proxy_rdns': self.proxy_rdns, 'proxy_type': self.proxy_type}

        return proxy

    def _get_sorted_broker_list(self):
        """
        Returns the Broker list sorted by response time low to high.

        :returns: {@code list}: Sorted list of brokers.
        """
        threads = []

        for broker in self.brokers:
            # pylint: disable=invalid-name
            t = threading.Thread(target=self._get_sorted_broker_list_worker, args=[broker])
            threads.append(t)
            t.daemon = True
            t.start()

        for t in threads:
            t.join()

        return sorted(self.brokers, key=lambda b: (b._response_time is None, b._response_time))

    def _get_fastest_broker_worker(self, broker):
        """Calculate the fastest (smallest response time) broker."""
        broker._connect_to_broker()
        self._queue.put(broker)

    def _get_fastest_broker(self):
        """
        Returns the Broker with the lowest response time.

        :returns: {@code dxlclient.broker.Broker}: Fastest broker.
        """
        brokers = self.brokers
        self._queue = Queue()

        for broker in brokers:
            # pylint: disable=invalid-name
            t = threading.Thread(target=self._get_fastest_broker_worker, args=[broker])
            t.daemon = True
            t.start()

        return self._queue.get(timeout=15)

    def _warn_for_missing_content(self):
        """
        Output a logger warning for any section or setting which is required
        for the client configuration but is missing a value.
        """
        for section in DxlClientConfig._SETTINGS:
            section_name, settings, section_required = section
            if section_required:
                if section_name not in self._config:
                    logger.warning("%s not defined in config file",
                                   section_name)
                for setting in settings:
                    setting_name, _, setting_required = setting
                    if setting_required and self._get_value_from_config(
                            setting_name) is None:
                        raise ValueError("{} was not defined in config file".
                                         format(setting_name))

    def _init_from_config_file(self, dxl_config_file):
        """
        Alternate constructor for creating a :class:`DxlClientConfig` instance
        from a configuration file.

        :param dxl_config_file: path to the configuration file
        :return: a :class:`DxlClientConfig` object corresponding to the
            specified configuration file
        """
        if not path.isfile(dxl_config_file):
            raise Exception("Can't parse config file")

        super(DxlClientConfig, self).__init__()

        self._config = ConfigObj(infile=dxl_config_file, raise_errors=True,
                                 file_error=True)
        self._config_path = path.dirname(dxl_config_file)

        self._warn_for_missing_content()

        broker_list = self._get_value_from_config(self._BROKERS_SECTION)
        if broker_list is None:
            broker_list = {}
            self._set_value_to_config(self._BROKERS_SECTION, broker_list)

        if len(broker_list) is 0:
            logger.warning("Broker list is empty")

        self._brokers = _get_brokers(self._get_value_from_config(
            self._BROKERS_SECTION))

        websocket_broker_list = self._get_value_from_config(self._BROKERS_WEBSOCKETS_SECTION)
        if websocket_broker_list is None:
            websocket_broker_list = {}
            self._set_value_to_config(self._BROKERS_WEBSOCKETS_SECTION, websocket_broker_list)

        self._websocket_brokers = _get_brokers(self._get_value_from_config(
            self._BROKERS_WEBSOCKETS_SECTION))

        self._init_common()

        client_id_from_config = self._get_value_from_config(
            self._CLIENT_ID_SETTING)
        if client_id_from_config:
            self._client_id = client_id_from_config

        if self._get_value_from_config(self._USE_WEBSOCKETS_SETTING):
            self._use_websockets = self._config.get(self._GENERAL_SECTION).as_bool(self._USE_WEBSOCKETS_SETTING)
        else:
            self._use_websockets = bool(self._websocket_brokers and not self._brokers)

        # Get Proxy Settings from Config file
        self._proxy_addr = self._get_value_from_config(self._PROXY_ADDRESS_SETTING)
        self._proxy_port = self._get_value_from_config(self._PROXY_PORT_SETTING)
        self._proxy_username = self._get_value_from_config(self._PROXY_USERNAME_SETTING)
        self._proxy_password = self._get_value_from_config(self._PROXY_PASSWORD_SETTING)

    @staticmethod
    def create_dxl_config_from_file(dxl_config_file):
        """

        This method allows creation of a :class:`DxlClientConfig` object from a
        specified configuration file. The information contained in the file has a one-to-one
        correspondence with the :class:`DxlClientConfig` constructor.

        .. code-block:: ini

            [General]
            useWebSocketBrokers=no

            [Certs]
            BrokerCertChain=c:\\\\certs\\\\brokercerts.crt
            CertFile=c:\\\\certs\\\\client.crt
            PrivateKey=c:\\\\certs\\\\client.key

            [Brokers]
            mybroker=mybroker;8883;mybroker.mcafee.com;192.168.1.12
            mybroker2=mybroker2;8883;mybroker2.mcafee.com;192.168.1.13

            [BrokersWebSockets]
            mybroker=mybroker;443;mybroker.mcafee.com;192.168.1.12
            mybroker2=mybroker2;443;mybroker2.mcafee.com;192.168.1.13

        The configuration file can be loaded as follows:

        .. code-block:: python

            from dxlclient.client_config import DxlClientConfig

            config = DxlClientConfig.create_dxl_config_from_file("c:\\\\certs\\\\dxlclient.cfg")

        :param dxl_config_file: Path to the configuration file
        :return: A :class:`DxlClientConfig` object corresponding to the specified configuration file
        """
        inst = DxlClientConfig.__new__(DxlClientConfig)
        # pylint: disable=protected-access
        inst._init_from_config_file(dxl_config_file)
        return inst

    def _get_file_path(self, cert_file_path):
        if self._config_path and cert_file_path \
                and not path.isfile(cert_file_path) \
                and not path.isabs(cert_file_path):
            file_path = path.join(self._config_path, cert_file_path)
            if path.isfile(file_path):
                cert_file_path = file_path
        return cert_file_path

    def _update_broker_config_models(self):
        """
        Set the contents of :meth:`brokers` into the configobj model,
        converting the list of :class:`dxlclient.broker.Broker` objects into a
        `dict` matching the format needed for the dxlclient config file.
        """
        self._update_broker_config_model(self._brokers, self._BROKERS_SECTION)
        self._update_broker_config_model(self._websocket_brokers, self._BROKERS_WEBSOCKETS_SECTION)

    def _update_broker_config_model(self, brokers, config_section):

        if brokers is None:
            self._set_value_to_config(config_section, None)
        else:
            brokers_for_config = OrderedDict()
            # A `unique_id` is not required for the in-memory representation of
            # a `Broker` object but it effectively is required when persisting
            # the broker configuration to a file. If no `unique_id` is found
            # on the `Broker` object, assign a random one as the key for the
            # broker config section so that the file can at least be persisted.
            for broker in brokers:
                unique_id = broker.unique_id if broker.unique_id else \
                    UuidGenerator.generate_id_as_string()
                brokers_for_config[unique_id] = broker._to_broker_string()

            # In order to attempt to preserve any comments that may have been
            # added to the configuration file for a pre-existing broker, this
            # code preserves the `configobj` model objects which already
            # exist for the brokers being set.
            current_brokers = self._get_value_from_config(
                config_section)
            if current_brokers is not None:
                brokers_to_delete = []

                for current_broker_key in current_brokers.keys():
                    if current_broker_key not in brokers_for_config:
                        brokers_to_delete.append(current_broker_key)

                # `configobj` model entries not present in the brokers to be set
                # are deleted - along with any associated comments.
                for broker_to_delete in brokers_to_delete:
                    del current_brokers[broker_to_delete]

                # The `merge` updates the values for pre-existing keys and adds in
                # new key/value pairs which are not already present in the config
                # model.
                current_brokers.merge(brokers_for_config)

    def write(self, file_path):
        """
        Create a DXL client configuration file from the current object. If the
        current object was created from a call to
        :meth:`create_dxl_config_from_file`, unchanged content should be
        preserved. For example, the original file may have the following:

        .. code-block:: ini

            [Certs]
            BrokerCertChain=c:\\\\certs\\\\brokercerts.crt
            CertFile=c:\\\\certs\\\\client.crt
            PrivateKey=c:\\\\certs\\\\client.key

            [Brokers]
            mybroker=mybroker;8883;mybroker.mcafee.com;192.168.1.12
            mybroker2=mybroker2;8883;mybroker2.mcafee.com;192.168.1.13

            [BrokersWebSockets]
            mybroker=mybroker;443;mybroker.mcafee.com;192.168.1.12
            mybroker2=mybroker2;443;mybroker2.mcafee.com;192.168.1.13

        The configuration could be loaded and changed as follows:

        .. code-block:: python

            from dxlclient.client_config import DxlClientConfig

            config = DxlClientConfig.create_dxl_config_from_file("c:\\\\certs\\\\dxlclient.config")
            config.cert_file = "c:\\\\\\\\certs\\\\\\\\newclient.crt"
            config.write("c:\\\\certs\\\\dxlclient.config")

        The resulting configuration should then appear as follows:

        .. code-block:: ini

            [Certs]
            BrokerCertChain=c:\\\\certs\\\\brokercerts.crt
            CertFile=c:\\\\certs\\\\newclient.crt
            PrivateKey=c:\\\\certs\\\\client.key

            [Brokers]
            mybroker=mybroker;8883;mybroker.mcafee.com;192.168.1.12
            mybroker2=mybroker2;8883;mybroker2.mcafee.com;192.168.1.13

            [BrokersWebSockets]
            mybroker=mybroker;443;mybroker.mcafee.com;192.168.1.12
            mybroker2=mybroker2;443;mybroker2.mcafee.com;192.168.1.13

        :param file_path: File at which to write the configuration. An attempt
            will be made to create any directories in the path which may not
            exist before writing the file.
        """
        self._update_broker_config_models()
        DxlUtils.makedirs(path.dirname(file_path))
        self._config.filename = file_path
        self._config.write()
