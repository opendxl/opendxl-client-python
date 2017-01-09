# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2017 McAfee Inc. - All Rights Reserved.
################################################################################
import logging
import threading
from Queue import Queue
import os.path as path

from ConfigParser import ConfigParser, NoSectionError, NoOptionError

from dxlclient import _BaseObject, _ObjectTracker
from dxlclient.broker import Broker
from dxlclient._uuid_generator import UuidGenerator
from dxlclient.exceptions import BrokerListError

################################################################################
#
# Static functions
#
################################################################################
logger = logging.getLogger(__name__)


class _DxlConfigParser(ConfigParser):
    """
    DxlClientConfig config file parser
    """

    def __init__(self):
        ConfigParser.__init__(self)
        _ObjectTracker.get_instance().obj_constructed(self)

    def __del__(self):
        _ObjectTracker.get_instance().obj_destructed(self)

    def get(self, section, option, show_warning=True):  # pylint: disable=arguments-differ
        """
        Gets the value of an option, if it doesn't exist return an empty string.

        :param section: Config section string
        :param option: Config option string
        :param show_warning: Show warning log message if option cannot be found in config file
        :return: Option value
        """
        option_value = ''
        try:
            option_value = ConfigParser.get(self, section, option)
        except (NoOptionError, NoSectionError):
            if show_warning:
                logger.warning(option + " was not defined in config file")
        return option_value


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
    if broker_list:
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
    except Exception, broker_error:
        raise BrokerListError("Broker list is not a valid JSON: " + str(broker_error))

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

    def __init__(self, broker_ca_bundle, cert_file, private_key, brokers):
        """
        Constructor parameters:

        :param broker_ca_bundle: The file name of a bundle containing the broker CA certificates in PEM format
        :param cert_file: The file name of the client certificate in PEM format
        :param private_key: The file name of the client private key in PEM format
        :param brokers: A list of :class:`dxlclient.broker.Broker` objects representing brokers comprising the
            DXL fabric. When invoking the :func:`dxlclient.client.DxlClient.connect` method, the
            :class:`dxlclient.client.DxlClient` will attempt to connect to the closest broker.
        """
        super(DxlClientConfig, self).__init__()

        client_id = UuidGenerator.generate_id_as_string()

        if not broker_ca_bundle:
            raise ValueError("Broker CA bundle not specified")

        if not cert_file:
            raise ValueError("Certificate file not specified")

        if not private_key:
            raise ValueError("Private key file not specified")

        if brokers is None:
            raise ValueError("Brokers were not specified")

        # The number of times to retry during connect
        self._connect_retries = self._DEFAULT_CONNECT_RETRIES
        # The keep alive interval
        self._keep_alive_interval = self._DEFAULT_MQTT_KEEP_ALIVE_INTERVAL
        # The reconnect back off multiplier
        self._reconnect_back_off_multiplier = self._DEFAULT_RECONNECT_BACK_OFF_MULTIPLIER
        # The reconnect delay (in seconds)
        self._reconnect_delay = self._DEFAULT_RECONNECT_DELAY
        # The maximum reconnect delay
        self._reconnect_delay_max = self._DEFAULT_RECONNECT_DELAY_MAX
        # The reconnect delay random
        self._reconnect_delay_random = self._DEFAULT_RECONNECT_DELAY_RANDOM
        # Whether to reconnect when disconnected
        self._reconnect_when_disconnected = self._DEFAULT_RECONNECT_WHEN_DISCONNECTED

        # The unique identifier of the client
        self._client_id = client_id
        # The list of brokers
        self.brokers = brokers
        # The filename of the CA bundle file in PEM format
        self.broker_ca_bundle = broker_ca_bundle
        # The filename of the client certificate in PEM format (must not have a password)
        self.cert_file = cert_file
        # The filename of the private key used to request the certificates
        self.private_key = private_key
        # Queue for getting the sorted broker list
        self._queue = None
        # The incoming message queue size
        self._incoming_message_queue_size = 1000
        # The incoming thread pool size
        self._incoming_message_thread_pool_size = 1

    def __del__(self):
        """destructor"""
        super(DxlClientConfig, self).__del__()

    @property
    def broker_ca_bundle(self):
        """
        The file name of a bundle containing the broker CA certificates in PEM format
        """
        return self._broker_ca_bundle

    @broker_ca_bundle.setter
    def broker_ca_bundle(self, broker_ca_bundle):
        self._broker_ca_bundle = broker_ca_bundle

    @property
    def cert_file(self):
        """
        The file name of the client certificate in PEM format
        """
        return self._cert_file

    @cert_file.setter
    def cert_file(self, cert_file):
        self._cert_file = cert_file

    @property
    def private_key(self):
        """
        The file name of the client private key in PEM format
        """
        return self._private_key

    @private_key.setter
    def private_key(self, private_key):
        self._private_key = private_key

    @property
    def brokers(self):
        """
        A list of :class:`dxlclient.broker.Broker` objects representing brokers comprising the
        DXL fabric. When invoking the :func:`dxlclient.client.DxlClient.connect` method, the
        :class:`dxlclient.client.DxlClient` will attempt to connect to the closest broker.
        """
        return self._brokers

    @brokers.setter
    def brokers(self, brokers):
        self._brokers = brokers

    @property
    def incoming_message_queue_size(self):
        """
        The queue size for incoming messages (will block when queue is full)
        """
        return self._incoming_message_queue_size

    @incoming_message_queue_size.setter
    def incoming_message_queue_size(self, incoming_message_queue_size):
        self._incoming_message_queue_size = incoming_message_queue_size

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

    def _set_brokers_from_json(self, broker_list):
        """
        Sets brokers list from JSON object.

        :param broker_list: Object containing dxl brokers. Should have this format:
        """
        brokers = _get_brokers(broker_list)
        if brokers is not None:
            self._brokers[:] = brokers

    def _get_sorted_broker_list_worker(self, broker):
        """Returns a sorted list of the brokers in this config."""
        broker._connect_to_broker()

    def _get_sorted_broker_list(self):
        """
        Returns the Broker list sorted by response time low to high.

        :returns: {@code list}: Sorted list of brokers.
        """
        threads = []

        for broker in self._brokers:
            # pylint: disable=invalid-name
            t = threading.Thread(target=self._get_sorted_broker_list_worker, args=[broker])
            threads.append(t)
            t.daemon = True
            t.start()

        for t in threads:
            t.join()

        return sorted(self._brokers, key=lambda b: (b._response_time is None, b._response_time))

    def _get_fastest_broker_worker(self, broker):
        """Calculate the fastest (smallest response time) broker."""
        broker._connect_to_broker()
        self._queue.put(broker)

    def _get_fastest_broker(self):
        """
        Returns the Broker with the lowest response time.

        :returns: {@code dxlclient.broker.Broker}: Fastest broker.
        """
        brokers = self._brokers
        self._queue = Queue()

        for broker in brokers:
            # pylint: disable=invalid-name
            t = threading.Thread(target=self._get_fastest_broker_worker, args=[broker])
            t.daemon = True
            t.start()

        return self._queue.get(timeout=15)

    @staticmethod
    def create_dxl_config_from_file(dxl_config_file):
        """

        This method allows creation of a :class:`DxlClientConfig` object from a
        specified configuration file. The information contained in the file has a one-to-one
        correspondence with the :class:`DxlClientConfig` constructor.

        .. code-block:: python

            [Certs]
            BrokerCertChain=c:\\\\certs\\\\brokercerts.crt
            CertFile=c:\\\\certs\\\\client.crt
            PrivateKey=c:\\\\certs\\\\client.key

            [Brokers]
            mybroker=mybroker;8883;mybroker.mcafee.com;192.168.1.12
            mybroker2=mybroker2;8883;mybroker2.mcafee.com;192.168.1.13

        The configuration file can be loaded as follows:

        .. code-block:: python

            from dxlclient.client_config import DxlClientConfig

            config = DxlClientConfig.create_dxl_config_from_file("c:\\\\certs\\\\dxlclient.cfg")

        :param dxl_config_file: Path to the configuration file
        :return: A :class:`DxlClientConfig` object corresponding to the specified configuration file
        """
        config_parser = _DxlConfigParser()

        if not config_parser.read(dxl_config_file):
            raise Exception("Can't parse config file")

        config_file_path = path.dirname(dxl_config_file)
        cert_file = DxlClientConfig._get_file_path(config_file_path, config_parser.get("Certs", "CertFile"))
        private_key = DxlClientConfig._get_file_path(config_file_path, config_parser.get("Certs", "PrivateKey"))
        cert_chain = DxlClientConfig._get_file_path(config_file_path, config_parser.get("Certs", "BrokerCertChain"))
        client_id = config_parser.get("General", "ClientId", False)

        client_config = DxlClientConfig(broker_ca_bundle=cert_chain,
                                        cert_file=cert_file, private_key=private_key, brokers=[])
        if client_id:
            client_config._client_id = client_id

        broker_list = {}
        try:
            brokers = config_parser.items("Brokers")
            for broker in brokers:
                broker_list[broker[0]] = broker[1]
        except NoSectionError:
            logger.warning("Brokers not defined in config file")

        if len(broker_list) is 0:
            logger.warning("Broker list is empty")

        client_config._set_brokers_from_json(broker_list)
        return client_config

    @staticmethod
    def _get_file_path(config_path, cert_file_path):
        if not path.isfile(cert_file_path) and not path.isabs(cert_file_path):
            file_path = path.join(config_path, cert_file_path)
            if path.isfile(file_path):
                cert_file_path = file_path
        return cert_file_path
