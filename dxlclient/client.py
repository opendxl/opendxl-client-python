# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
################################################################################

"""
Contains the :class:`DxlClient` class, which is responsible for all
communication with the Data Exchange Layer (DXL) fabric.
"""

from __future__ import absolute_import
import threading
import logging
import ssl
import traceback
import random
import time

import pahoproxy.client as mqtt
from dxlclient import _BaseObject
from dxlclient.client_config import DxlClientConfig
import dxlclient._callback_manager as callback_manager
from dxlclient._request_manager import RequestManager
from dxlclient.exceptions import DxlException
from dxlclient.message import Message, Event, Request, Response, ErrorResponse
from dxlclient._thread_pool import ThreadPool
from dxlclient.exceptions import WaitTimeoutException
from dxlclient.service import _ServiceManager
from dxlclient._uuid_generator import UuidGenerator
from ._dxl_utils import DxlUtils

__all__ = [
    # Callbacks
    "_on_connect", "_on_disconnect", "_on_message", "_on_log",
    "_on_subscribe", "_on_unsubscribe",
    # Client
    "DxlClient",
    # Constants
    "DXL_ERR_AGAIN", "DXL_ERR_SUCCESS", "DXL_ERR_INVALID", "DXL_ERR_INTERRUPT",
]


logger = logging.getLogger(__name__)

DXL_ERR_AGAIN = -1
DXL_ERR_SUCCESS = 0
DXL_ERR_INVALID = 1
DXL_ERR_INTERRUPT = 2

################################################################################
#
# Callbacks
#
################################################################################


def _on_connect(client, userdata, flags, rc): # pylint: disable=invalid-name
    """
    Called when the client connects to the broker.

    :param client: The Paho MQTT client reference
    :param userdata: The user data object provided
    :param rc: The result code
    :return: None
    """
    del flags # unused
    t = threading.Thread(target=_on_connect_run, args=[client, userdata, rc])
    t.daemon = True
    t.start()


def _on_connect_run(client, userdata, rc): # pylint: disable=invalid-name
    """
    Worker method that is invoked when the client connects to the broker.

    :param client: The Paho MQTT client reference
    :param userdata: The user data object provided
    :param rc: The result code
    :return: None
    """
    if not isinstance(userdata, DxlClient):
        raise ValueError("User data object not specified")

    self = userdata

    with self._connected_lock:
        self._connected = True

        logger.debug("Connected with result code %s", str(rc))

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        with self._subscriptions_lock:
            for subscription in self._subscriptions:
                try:
                    logger.debug("Subscribing to %s", subscription)
                    result, mid = client.subscribe(subscription)
                    self._wait_for_packet_ack(result, mid,
                                              "subscription to " +
                                              subscription)
                except Exception as ex: # pylint: disable=broad-except
                    logger.error("Error during subscribe: %s", str(ex))
                    logger.debug(traceback.format_exc())

        if self._service_manager:
            self._service_manager.on_connect()

        # Notify that connection status has changed
        self._connected_wait_condition.notify_all()


def _on_disconnect(client, userdata, rc): # pylint: disable=invalid-name
    """
    Called when the client disconnects from the broker.

    :param client: The Paho MQTT client reference
    :param userdata: The user data object provided
    :param rc: The result code
    :return: None
    """
    t = threading.Thread(target=_on_disconnect_run, args=[client, userdata, rc])
    t.daemon = True
    t.start()


def _on_disconnect_run(client, userdata, rc):  # pylint: disable=invalid-name
    """
    Worker method that is invoked when the client disconnects from the broker.

    :param client: The Paho MQTT client reference
    :param userdata: The user data object provided
    :param rc: The result code
    :return: None
    """
    del client # unused
    # Check userdata; this needs to be an instance of the DxlClient
    if not isinstance(userdata, DxlClient):
        raise ValueError("User data object not specified")
    self = userdata

    with self._connected_lock:
        self._connected = False
        self._reset_current_broker()
        self._connected_wait_condition.notify_all()

    if rc == 0:
        logger.debug("Disconnected with result code %s", str(rc))
    else:
        logger.error("Unexpected disconnect with result code %s", str(rc))
        # Disconnect the client
        self._disconnect()
        # Connect the client
        if self.config.reconnect_when_disconnected:
            self._start_connect_thread()


def _on_message(client, userdata, msg): # pylint: disable=invalid-name
    """
    Called when a message has been received on a topic that the client subscribes to.
    self callback will be called for every message received.

    :param client: The Paho MQTT client reference
    :param userdata: The user data object provided
    :param msg: The message object
    :return: None
    """
    del client # unused
    # Check userdata; this needs to be an instance of the DxlClient
    if userdata is None or not isinstance(userdata, DxlClient):
        raise ValueError("Client reference not specified")
    self = userdata

    logger.debug("Message received for topic %s", msg.topic)

    # TODO: The behavior is one thread per message, but the individual callbacks are handled sequential.
    # TODO: self is the same as in the Java client, but is not ideal.  One plugin could block the whole
    # TODO: execution.

    try:
        self._thread_pool.add_task(self._handle_message, channel=msg.topic, payload=msg.payload)
    except Exception:  # pylint: disable=broad-except
        logger.exception("Error handling message")


def _on_log(client, userdata, level, buf):
    """
    Called when the client has log information. Define to allow debugging.
    The level variable gives the severity of the message and will be one of
    MQTT_LOG_INFO, MQTT_LOG_NOTICE, MQTT_LOG_WARNING, MQTT_LOG_ERR, and
    MQTT_LOG_DEBUG. The message itself is in buf.

    :param client: The Paho MQTT client reference
    :param userdata: The user data object provided
    :param level: The severity of the message
    :param buf: The message itself
    :return: None
    """
    del client, userdata # unused
    if level == mqtt.MQTT_LOG_INFO:
        logger.info("MQTT: %s", str(buf))
    elif level == mqtt.MQTT_LOG_NOTICE:
        logger.info("MQTT: %s", str(buf))
    elif level == mqtt.MQTT_LOG_WARNING:
        logger.warning("MQTT: %s", str(buf))
    elif level == mqtt.MQTT_LOG_ERR:
        logger.error("MQTT: %s", str(buf))
    elif level == mqtt.MQTT_LOG_DEBUG:
        logger.debug("MQTT: %s", str(buf))

def _on_subscribe(client, userdata, mid, granted_qos):
    """
    Called when an ack message is received for a topic subscription that the
    client has issued.

    :param client: The Paho MQTT client reference
    :param userdata: The user data object provided
    :param mid: The message id of the MQTT subscription packet which corresponds
        to the ack packet.
    :param granted_qos: List of integers which gives the QoS level that the
        broker has granted for the subscription request.
    :return: None
    """
    del client, granted_qos # unused
    # Check userdata; this needs to be an instance of the DxlClient
    if not isinstance(userdata, DxlClient):
        raise ValueError("Client reference not specified")
    self = userdata
    self._on_packet_ack(mid)

def _on_unsubscribe(client, userdata, mid):
    """
    Called when an ack message is received for a topic unsubscription that the
    client has issued.

    :param client: The Paho MQTT client reference
    :param userdata: The user data object provided
    :param mid: The message id of the MQTT unsubscription packet which
        corresponds to the ack packet.
    :return: None
    """
    del client # unused
    # Check userdata; this needs to be an instance of the DxlClient
    if not isinstance(userdata, DxlClient):
        raise ValueError("Client reference not specified")
    self = userdata
    self._on_packet_ack(mid)

################################################################################
#
# DxlClient
#
################################################################################


class DxlClient(_BaseObject):

    """
    The :class:`DxlClient` class is responsible for all communication with the Data Exchange Layer (DXL)
    fabric (it can be thought of as the "main" class). All other classes exist to support the functionality
    provided by the client.

    The following example demonstrates the configuration of a :class:`DxlClient` instance and
    connecting it to the fabric:

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

    **NOTE:** The preferred way to construct the client is via the Python "with" statement as shown above. The "with"
    statement ensures that resources associated with the client are properly cleaned up when the block is exited.

    The following modules support the client:

    - :mod:`dxlclient.client_config` : See this module for information on configuring the :class:`DxlClient`
    - :mod:`dxlclient.message` : See this module for information on the different types of messages that can be
      exchanged over the DXL fabric
    - :mod:`dxlclient.callbacks` : See this module for information on registering "callbacks" that are used to
      receive messages via the :class:`DxlClient`. This module also includes an example that demonstrate how to
      send :class:`dxlclient.message.Event` messages.
    - :mod:`dxlclient.service` : See this module for information on registering "services" with the DXL fabric.
      This module also includes an example that demonstrates how to invoke a DXL service via the :class:`DxlClient`.
    """

    # The default "reply-to" prefix. self is typically used for setting up response
    # channels for requests, etc.
    _REPLY_TO_PREFIX = "/mcafee/client/"
    # The default wait time for a synchronous request, defaults to 1 hour
    _DEFAULT_WAIT = 60 * 60
    # The default wait for policy delay (in seconds)
    _DEFAULT_WAIT_FOR_POLICY_DELAY = 2
    # The default minimum amount of threads in a thread pool
    _DEFAULT_MIN_POOL_SIZE = 10
    # The default maximum amount of threads in a thread pool
    _DEFAULT_MAX_POOL_SIZE = 25
    # The default quality of server (QOS) for messages
    _DEFAULT_QOS = 0
    # The default connect wait
    _DEFAULT_CONNECT_WAIT = 10  # seconds
    # Maximum time to wait for a subscription / unsubscription packet to be
    # acked (in seconds)
    _MAX_PACKET_ACK_WAIT = 2 * 60

    def __init__(self, config):
        """
        Constructor parameters:

        :param config: The :class:`dxlclient.client_config.DxlClientConfig` object containing the configuration
            settings for the client.
        """

        # Ensure that variables which may be referenced from the destructor
        # are pre-initialized in the event that an error is raised from the
        # constructor.
        self._destroy_lock = threading.RLock()
        self._destroyed = False
        self._service_manager = None
        self._request_manager = None
        self._thread_pool = None
        self._client = None

        # The flag for the connection state
        self._connected = False

        super(DxlClient, self).__init__()

        if config is None or not isinstance(config, DxlClientConfig):
            raise ValueError("Client configuration not specified")

        # The client configuration
        self._config = config
        # The lock for the client configuration
        self._config_lock = threading.RLock()
        # The condition associated with the client configuration
        self._config_lock_condition = threading.Condition(self._config_lock)

        # The lock for the flag for the connection state
        self._connected_lock = threading.RLock()
        # The condition for the flag on connection state
        self._connected_wait_condition = threading.Condition(self._connected_lock)
        # The current broker the client is connected to
        self._current_broker = None
        # The lock for the current broker the client is connected to
        self._current_broker_lock = threading.RLock()

        # The default wait time for a synchronous request
        self._default_wait = self._DEFAULT_WAIT

        # The wait for policy delay (in seconds)
        self._wait_for_policy_delay = self._DEFAULT_WAIT_FOR_POLICY_DELAY

        # The minimum amount of threads in a thread pool
        self._core_pool_size = self._DEFAULT_MIN_POOL_SIZE
        # The maximum amount of threads in a thread pool
        self._maximum_pool_size = self._DEFAULT_MAX_POOL_SIZE

        # The quality of server (QOS) for messages
        self._qos = self._DEFAULT_QOS
        # The "reply-to" prefix. self is typically used for setting up response
        # channels for requests, etc.
        self._reply_to_topic = self._REPLY_TO_PREFIX + self._config._client_id

        # The request callbacks manager
        self._request_callbacks = callback_manager._RequestCallbackManager()
        # The response callbacks manager
        self._response_callbacks = callback_manager._ResponseCallbackManager()
        # The event callbacks manager
        self._event_callbacks = callback_manager._EventCallbackManager()

        # The current list of subscriptions
        self._subscriptions = set()
        # The lock for the current list of subscriptions
        self._subscriptions_lock = threading.RLock()
        # HTTP Proxy for connecting through web sockets
        self._proxy = self._config._get_http_proxy()
        # The underlying MQTT client instance
        self._client = self._get_mqtt_client()
        # Set the callback methods for MQTT client
        self._set_mqtt_client_callbacks()
        # pylint: disable=no-member
        # The MQTT client TLS configuration
        self._client.tls_set(config.broker_ca_bundle,
                             certfile=config.cert_file,
                             keyfile=config.private_key,
                             cert_reqs=ssl.CERT_REQUIRED,
                             tls_version=ssl.PROTOCOL_SSLv23,
                             ciphers=None)
        # The MQTT client TLS configuration to bypass hostname validation
        self._client.tls_insecure_set(True)

        # Generate a message pool prefix
        self._message_pool_prefix = "DxlMessagePool-" + UuidGenerator.generate_id_as_string()

        # The thread pool for message handling
        self._thread_pool = ThreadPool(
            num_threads=config.incoming_message_thread_pool_size,
            queue_size=config.incoming_message_queue_size,
            thread_prefix=self._message_pool_prefix)

        # Subscribe to the client reply channel
        self.subscribe(self._reply_to_topic)

        # The request manager (manages synchronous and asynchronous request callbacks,
        # notifications, etc.).
        self._request_manager = RequestManager(client=self)

        # The service manager (manages services request callbacks, notifications, etc.).
        self._service_manager = _ServiceManager(client=self)

        # The loop thread
        self._thread = None
        # The loop thread terminate flag
        self._thread_terminate = False

        # The lock for the connect thread
        self._connect_wait_lock = threading.RLock()
        # The condition associated with the client configuration
        self._connect_wait_condition = threading.Condition(self._connect_wait_lock)

        self._acked_packets = set()
        self._wait_packet_ack_condition = threading.Condition()

    def __del__(self):
        """destructor"""
        super(DxlClient, self).__del__()
        # Avoid waiting for all of the threads in the thread pool to complete
        # since they may never shutdown completely (leading to a hang) if the
        # destructor is called at process shutdown.
        self._destroy(wait_complete=False)

    def __enter__(self):
        """Enter with"""
        return self

    def __exit__(self, exc_type, exc_value, trace):
        """Exit with"""
        self.destroy()

    @property
    def config(self):
        """
        The :class:`dxlclient.client_config.DxlClientConfig` instance that was specified when the
        client was constructed.

        See :mod:`dxlclient.client_config` for more information on configuring the client.
        """
        with self._config_lock:
            return self._config

    @property
    def connected(self):
        """Whether the client is currently connected to the DXL fabric."""
        with self._connected_lock:
            return self._connected

    def connect(self):
        """
        Attempts to connect the client to the DXL fabric.

        This method does not return until either the client has connected to the fabric or it has exhausted
        the number of retries configured for the client causing an exception to be raised.

        Several attributes are available for controlling the client retry behavior:

        - :attr:`dxlclient.client_config.DxlClientConfig.connect_retries` : The maximum number of connection attempts
          for each :class:`dxlclient.broker.Broker` specified in the :class:`dxlclient.client_config.DxlClientConfig`
        - :attr:`dxlclient.client_config.DxlClientConfig.reconnect_delay` : The initial delay between retry attempts.
          The delay increases ("backs off") as subsequent connection attempts are made.
        - :attr:`dxlclient.client_config.DxlClientConfig.reconnect_back_off_multiplier` : Multiples the current
          reconnect delay by this value on subsequent connect retries. For example, a current delay of 3 seconds
          with a multiplier of 2 would result in the next retry attempt being in 6 seconds.
        - :attr:`dxlclient.client_config.DxlClientConfig.reconnect_delay_random` : A randomness delay percentage
          (between 0.0 and 1.0) that is used to increase the current retry delay by a random amount for the purpose
          of preventing multiple clients from having the same retry pattern
        - :attr:`dxlclient.client_config.DxlClientConfig.reconnect_delay_max` : The maximum delay between retry attempts
        """
        if self.connected:
            raise DxlException("Already connected")

        if self._thread is not None:
            raise DxlException("Already trying to connect")

        # Start the connect thread
        self._start_connect_thread(connect_retries=self.config.connect_retries)

        # Wait for the connect thread to finish
        if self._thread is not None:
            while self._thread.isAlive():
                self._thread.join(1)
            self._thread = None

        # Wait for the callback to be invoked
        with self._connected_lock:
            if not self.connected:
                self._connected_wait_condition.wait(self._DEFAULT_CONNECT_WAIT)

        # Check if we were connected
        if not self.connected:
            raise DxlException("Failed to establish connection")

    def _start_connect_thread(self, connect_retries=-1):
        self._thread = threading.Thread(target=self._connect_thread_main, args=[connect_retries])
        self._thread.daemon = True
        self._thread.start()

    def destroy(self):
        """
        Destroys the client (releases all associated resources).

        **NOTE:** Once the method has been invoked, no other calls should be made to the client.

        Also note that this method should rarely be called directly. Instead, the preferred usage of the
        client is via a Python "with" statement as shown below:

        .. code-block:: python

            # Create the DXL client
            with DxlClient(config) as dxl_client:

                # Connect to the fabric
                dxl_client.connect()

        The "with" statement ensures that resources associated with the client are properly cleaned up when the block
        is exited (the :func:`destroy` method is invoked).

        """
        self._destroy()

    def _destroy(self, wait_complete=True):
        with self._destroy_lock:
            if not self._destroyed:
                if self._service_manager:
                    self._service_manager.destroy()
                    self._service_manager = None

                if self._request_manager:
                    self._request_manager.destroy()
                    self._request_manager = None

                self.disconnect()

                if self._thread_pool:
                    self._thread_pool.shutdown(wait_complete)

                self._config = None

                if self._client:
                    self._client.user_data_set(None)
                    self._client = None

                self._destroyed = True

    def disconnect(self):
        """
        Attempts to disconnect the client from the DXL fabric.
        """
        if self._connected:
            self._disconnect()
        else:
            logger.warning("Trying to disconnect a disconnected client.")

    def _disconnect(self):
        if self._service_manager:
            self._service_manager.on_disconnect()

        logger.debug("Waiting for thread pool completion...")
        self._thread_pool.wait_completion()

        for subscription in self._subscriptions:
            if self.connected:
                try:
                    logger.debug("Unsubscribing from %s", subscription)
                    result, mid = self._client.unsubscribe(subscription)
                    self._wait_for_packet_ack(result, mid,
                                              "unsubscription to " +
                                              subscription)
                except Exception as ex:  # pylint: disable=broad-except
                    logger.error("Error during unsubscribe: %s", str(ex))
                    logger.debug(traceback.format_exc())

        # In case of a reconnect after connection loss, the event loop will
        # not be stopped and the client will not be forcefully disconnected.
        logger.debug("Stopping event loop...")
        self._client.loop_stop()
        logger.debug("Trying to disconnect client...")
        self._client.disconnect()
        logger.debug("Disconnected.")

        # Make sure the connection loop is done
        if self._thread is not None:
            logger.debug("Waiting for the thread to terminate...")
            self._thread_terminate = True
            with self._connect_wait_lock:
                self._connect_wait_condition.notifyAll()
            while self._thread.isAlive():
                self._thread.join(1)
            self._thread = None
            logger.debug("Thread terminated.")

        # Wait for the callback to be invoked
        with self._connected_lock:
            if self.connected:
                self._connected_wait_condition.wait(self._DEFAULT_CONNECT_WAIT)

        # Check if we were disconnected
        if self.connected:
            raise DxlException("Failed to disconnect")

    def _connect_thread_main(self, connect_retries):
        """
        The connection thread main function
        """
        self._thread_terminate = False
        self._loop_until_connected(connect_retries)

    def _connect(self, brokers): # pylint: disable=too-many-branches
        """
        Internal function that attempts to connect to one of the given brokers.

        :param brokers: The (sorted) list of brokers
        """
        self._reset_current_broker()
        keep_alive_interval = self.config.keep_alive_interval
        latest_ex = None

        for broker in brokers:
            if self._thread_terminate:
                break
            if broker._response_time is not None:
                try:
                    logger.info("Trying to connect to broker %s...", broker.to_string())
                    if broker._response_from_ip_address:
                        self._client.connect(broker.ip_address, broker.port, keep_alive_interval, **self._proxy)
                    else:
                        self._client.connect(broker.host_name, broker.port, keep_alive_interval, **self._proxy)
                    self._current_broker = broker
                    break
                except Exception as ex:  # pylint: disable=broad-except
                    logger.error("Failed to connect to broker %s: %s",
                                 broker.to_string(),
                                 str(ex))
                    logger.debug(traceback.format_exc())
                    latest_ex = ex

        if self._current_broker is None:
            for broker in brokers:
                if self._thread_terminate:
                    break
                try:
                    logger.info(
                        "Trying to connect to broker (host name) %s...", broker.to_string())
                    self._client.connect(broker.host_name, broker.port, keep_alive_interval)
                    self._current_broker = broker
                    break
                except Exception as ex:  # pylint: disable=broad-except
                    logger.error("Failed to connect to broker (host name) %s: %s",
                                 broker.to_string(), str(ex))
                    logger.debug(traceback.format_exc())
                    latest_ex = ex

                if self._thread_terminate:
                    break
                if self._current_broker is None and broker.ip_address:
                    try:
                        logger.info(
                            "Trying to connect to broker (IP address) %s (%s:%d)...",
                            broker.unique_id, broker.ip_address, broker.port)
                        self._client.connect(broker.ip_address, broker.port, keep_alive_interval)
                        self._current_broker = broker
                        break
                    except Exception as ex:  # pylint: disable=broad-except
                        logger.error("Failed to connect to broker (IP address) %s: %s",
                                     broker.to_string(), str(ex))
                        logger.debug(traceback.format_exc())
                        latest_ex = ex

        if self._current_broker is not None:
            logger.info("Connected to broker %s",
                        self._current_broker.unique_id)
        else:
            if latest_ex is not None:
                raise latest_ex  # pylint: disable=raising-bad-type

    def _loop_until_connected(self, connect_retries):
        # pylint: disable=too-many-branches
        # The client is already connected
        if self.connected:
            logger.error("Already connected")
            return DXL_ERR_INVALID

        logger.info("Waiting for broker list...")
        self._config_lock.acquire()
        try:
            while not self._thread_terminate and not self._config.brokers:
                self._config_lock_condition.wait(self._wait_for_policy_delay)
                if not self._config.brokers:
                    logger.debug("No broker defined. Waiting for broker list...")
        finally:
            self._config_lock.release()

        if self._thread_terminate is True:
            logger.debug("Stopping...")
            return DXL_ERR_INTERRUPT

        logger.debug("Checking brokers...")
        brokers = self._config._get_sorted_broker_list()

        logger.info("Trying to connect...")
        retries = connect_retries
        retry_delay = self.config.reconnect_delay
        first_attempt = True
        latest_ex = None
        latest_ex_traceback = None

        while not self._thread_terminate and (connect_retries < 0 or retries >= 0):
            if not first_attempt:
                # Determine retry delay
                retry_delay_max = self.config.reconnect_delay_max
                if retry_delay > retry_delay_max:
                    retry_delay = retry_delay_max
                # Apply random after max (so we still have randomness, may exceed maximum)
                retry_delay += ((self.config.reconnect_delay_random * retry_delay) * random.random())

                logger.error("Retrying connect in %s seconds: %s", str(retry_delay), str(latest_ex))

                # Wait...
                with self._connect_wait_lock:
                    self._connect_wait_condition.wait(retry_delay)

                # Update retry delay
                retry_delay *= self.config.reconnect_back_off_multiplier

            try:
                self._connect(brokers)
                break
            except Exception as ex: # pylint: disable=broad-except
                # Track latest exception
                latest_ex = ex
                latest_ex_traceback = traceback.format_exc()

            first_attempt = False
            retries -= 1

        if self._thread_terminate is True:
            logger.info("Stopping...")
            return DXL_ERR_INTERRUPT

        if not self._current_broker:
            if latest_ex:
                logger.error("Error during connect: %s", latest_ex)
            if latest_ex_traceback:
                logger.debug(latest_ex_traceback)

        logger.debug("Launching event loop...")

        self._client.loop_start()

        return DXL_ERR_SUCCESS

    @property
    def current_broker(self):
        """
        The :class:`dxlclient.broker.Broker` that the client is currently connected to. ``None`` is returned
        if the client is not currently connected to a :class:`dxlclient.broker.Broker`.
        """
        with self._current_broker_lock:
            return self._current_broker if self.connected else None

    def _set_current_broker(self, current_broker):
        """
        Internal method. Sets the current broker.

        :param current_broker: {@code dxlclient.broker.Broker} to set as current broker.
        """
        with self._current_broker_lock:
            self._current_broker = current_broker

    def _reset_current_broker(self):
        """
        Clean current broker.
        """
        with self._current_broker_lock:
            self._current_broker = None

    def subscribe(self, topic):
        """
        Subscribes to the specified topic on the DXL fabric. This method is typically used in
        conjunction with the registration of :class:`dxlclient.callbacks.EventCallback` instances
        via the :func:`add_event_callback` method.

        The following is a simple example of using this:

        .. code-block:: python

            from dxlclient.callbacks import EventCallback

            class MyEventCallback(EventCallback):
                def on_event(self, event):
                    print("Received event! " + event.source_client_id)

            dxl_client.add_event_callback("/testeventtopic", MyEventCallback(), False)
            dxl_client.subscribe("/testeventtopic")

        **NOTE:** By default when registering an event callback the client will automatically subscribe to the topic.
        In this example the :func:`dxlclient.client.DxlClient.add_event_callback` method is invoked with the
        ``subscribe_to_topic`` parameter set to ``False`` preventing the automatic subscription.

        :param topic: The topic to subscribe to
        """
        logger.debug("%s(): Waiting for Subscriptions lock...", DxlUtils.func_name())
        self._subscriptions_lock.acquire()
        try:
            if topic not in self._subscriptions:
                self._subscriptions.add(topic)
                if self.connected:
                    result, mid = self._client.subscribe(topic)
                    self._wait_for_packet_ack(result, mid,
                                              "subscription to " + topic)
        finally:
            logger.debug("%s(): Releasing Subscriptions lock.", DxlUtils.func_name())
            self._subscriptions_lock.release()

    def unsubscribe(self, topic):
        """
        Unsubscribes from the specified topic on the DXL fabric.

        See the :func:`subscribe` method for more information on subscriptions.

        :param topic: The topic to unsubscribe from
        """
        logger.debug("%s(): Waiting for Subscriptions lock...", DxlUtils.func_name())
        self._subscriptions_lock.acquire()
        try:
            if topic in self._subscriptions:
                if self.connected:
                    result, mid = self._client.unsubscribe(topic)
                    self._wait_for_packet_ack(result, mid,
                                              "unsubscription to " + topic)
        finally:
            if topic in self._subscriptions:
                self._subscriptions.remove(topic)
            logger.debug("%s(): Releasing Subscriptions lock.", DxlUtils.func_name())
            self._subscriptions_lock.release()

    def _wait_for_packet_ack(self, result, mid, description):
        """
        Wait until an ack packet is delivered for an MQTT message or the broker
        connection is dropped. This should only be called once for a specific
        packet. If this function is called additional times for a specific
        packet, the function will pause until the amount of time in
        MAX_PACKET_ACK_WAIT is reached and then throw a WaitTimeoutException.
        :param result: Result delivered by MQTT for the attempt to send the
            original packet. If the Result is anything other than
            MQTT_ERR_SUCCESS this function will assume that the original packet
            was never sent and, therefore, that the function would not need to
            wait for a corresponding ack packet.
        :param mid: The message id of the MQTT packet which corresponds to the
            ack packet.
        :param description: Text string to include in the exception this
            method raises if a timeout occurs while waiting for the ACK packet.
        :raise WaitTimeoutException: if the ack packet is not received before
            a timeout is reached.
        """
        with self._wait_packet_ack_condition:
            if result == mqtt.MQTT_ERR_SUCCESS:
                start = time.time()
                try:
                    time_remaining = self._MAX_PACKET_ACK_WAIT
                    while mid not in self._acked_packets and \
                            time_remaining > 0:
                        self._wait_packet_ack_condition.wait(
                            time_remaining)
                        time_remaining = start - time.time() + \
                                         self._MAX_PACKET_ACK_WAIT
                    if mid not in self._acked_packets:
                        raise WaitTimeoutException("Timeout waiting for " +
                                                   description)
                finally:
                    if mid in self._acked_packets:
                        self._acked_packets.remove(mid)

    def _on_packet_ack(self, mid):
        """
        Callback invoked when a ack packet is received.

        :param mid: The message id of the MQTT packet which corresponds to the
            ack packet.
        """
        with self._wait_packet_ack_condition:
            self._acked_packets.add(mid)
            self._wait_packet_ack_condition.notify_all()

    @property
    def subscriptions(self):
        """
        A tuple containing the topics that the client is currently subscribed to

        See :func:`subscribe` for more information on adding subscriptions
        """
        logger.debug("%s(): Waiting for Subscriptions lock...", DxlUtils.func_name())
        self._subscriptions_lock.acquire()
        try:
            return tuple(self._subscriptions)
        finally:
            logger.debug("%s(): Releasing Subscriptions lock.", DxlUtils.func_name())
            self._subscriptions_lock.release()

    def sync_request(self, request, timeout=_DEFAULT_WAIT):
        """
        Sends a :class:`dxlclient.message.Request` message to a remote DXL service.

        See module :mod:`dxlclient.service` for more information on DXL services.

        :param request: The :class:`dxlclient.message.Request` message to send to a remote DXL service
        :param timeout: The amount of time (in seconds) to wait for the :class:`dxlclient.message.Response`
            to the request. If the timeout is exceeded an exception will be raised. Defaults to ``3600``
            seconds (1 hour)
        """
        if threading.currentThread().name.startswith(self._message_pool_prefix):
            raise DxlException("Synchronous requests may not be invoked while handling an incoming message. " +
                               "The synchronous request must be made on a different thread.")

        return self._request_manager.sync_request(request, timeout)

    def async_request(self, request, response_callback=None):
        """
        Sends a :class:`dxlclient.message.Request` message to a remote DXL service asynchronously.
        This method differs from :func:`sync_request` due to the fact that it returns to the caller
        immediately after delivering the :class:`dxlclient.message.Request` message to the DXL fabric (It does
        not wait for the corresponding :class:`dxlclient.message.Response` to be received).

        An optional :class:`dxlclient.callbacks.ResponseCallback` can be specified. This callback will be invoked
        when the corresponding :class:`dxlclient.message.Response` message is received by the client.

        See module :mod:`dxlclient.service` for more information on DXL services.

        :param request: The :class:`dxlclient.message.Request` message to send to a remote DXL service
        :param response_callback: An optional :class:`dxlclient.callbacks.ResponseCallback` that will be invoked
            when the corresponding :class:`dxlclient.message.Response` message is received by the client.
        """
        return self._request_manager.async_request(request, response_callback)

    def _get_async_callback_count(self):
        """
        Returns the count of async callbacks that are waiting for a response
        :return: The count of async callbacks that are waiting for a response
        """
        return self._request_manager._get_async_callback_count()

    def _publish_message(self, channel, payload, qos):
        """
        Publishes the specified message

        :param channel: The channel to publish on
        :param payload: The message content
        :param qos: The quality of service (QOS)
        """
        self._client.publish(topic=channel, payload=payload, qos=qos)

    def _send_request(self, request):
        """
        Sends the specified request to the DXL fabric.

        :param request: The request to send to the DXL fabric
        """
        if request is None or not isinstance(request, Request):
            raise ValueError("Invalid or unspecified request object")
        request.reply_to_topic = self._reply_to_topic
        self._publish_message(request.destination_topic, request._to_bytes(), self._qos)

    def send_response(self, response):
        """
        Attempts to deliver the specified :class:`dxlclient.message.Response` message to the DXL fabric.
        The fabric will in turn attempt to deliver the response back to the client who sent the
        corresponding :class:`dxlclient.message.Request`.

        See module :mod:`dxlclient.message` for more information on message types, how they are delivered to
        remote clients, etc.

        See module :mod:`dxlclient.service` for more information on DXL services.

        :param event: The :class:`dxlclient.message.Event` to send
        """
        if response is None or not isinstance(response, Response):
            raise ValueError("Invalid or unspecified response object")
        self._publish_message(response.destination_topic, response._to_bytes(), self._qos)

    def send_event(self, event):
        """
        Attempts to deliver the specified :class:`dxlclient.message.Event` message to the DXL fabric.

        See module :mod:`dxlclient.message` for more information on message types, how they are delivered to
        remote clients, etc.

        :param event: The :class:`dxlclient.message.Event` to send
        """
        if event is None or not isinstance(event, Event):
            raise ValueError("Invalid or unspecified event object")
        self._publish_message(event.destination_topic, event._to_bytes(), self._qos)

    def add_request_callback(self, topic, request_callback):
        """
        Adds a :class:`dxlclient.callbacks.RequestCallback` to the client for the specified topic.
        The callback will be invoked when :class:`dxlclient.message.Request` messages are received by the client
        on the specified topic. A topic of ``None`` indicates that the callback should receive
        :class:`dxlclient.message.Request` messages for all topics (no filtering).

        **NOTE:** Usage of this method is quite rare due to the fact that registration of
        :class:`dxlclient.callbacks.RequestCallback` instances with the client occurs automatically when
        registering a service. See module :mod:`dxlclient.service` for more information on DXL services.

        :param topic: The topic to receive :class:`dxlclient.message.Request` messages on. A topic of ``None`` indicates
            that the callback should receive :class:`dxlclient.message.Request` messages for all topics (no filtering).
        :param request_callback: The :class:`dxlclient.callbacks.RequestCallback` to be invoked when a
            :class:`dxlclient.message.Request` message is received on the specified topic
        """
        self._request_callbacks.add_callback(("" if topic is None else topic), request_callback)

    def remove_request_callback(self, topic, request_callback):
        """
        Removes a :class:`dxlclient.callbacks.RequestCallback` from the client for the specified topic. This method
        must be invoked with the same arguments as when the callback was originally registered via
        :func:`add_request_callback`.

        :param topic: The topic to remove the callback for
        :param request_callback: The :class:`dxlclient.callbacks.RequestCallback` to be removed for the specified topic
        """
        self._request_callbacks.remove_callback(("" if topic is None else topic), request_callback)

    def add_response_callback(self, topic, response_callback):
        """
        Adds a :class:`dxlclient.callbacks.ResponseCallback` to the client for the specified topic.
        The callback will be invoked when :class:`dxlclient.message.Response` messages are received by the client
        on the specified topic. A topic of ``None`` indicates that the callback should receive
        :class:`dxlclient.message.Response` messages for all topics (no filtering).

        **NOTE:** Usage of this method is quite rare due to the fact that the use of
        :class:`dxlclient.callbacks.ResponseCallback` instances are typically limited to invoking a
        remote DXL service via the :func:`async_request` method.

        :param topic: The topic to receive :class:`dxlclient.message.Request` messages on. A topic of ``None`` indicates
            that the callback should receive :class:`dxlclient.message.Request` messages for all topics (no filtering).
        :param request_callback: The :class:`dxlclient.callbacks.RequestCallback` to be invoked when a
            :class:`dxlclient.message.Request` message is received on the specified topic
        """
        self._response_callbacks.add_callback(("" if topic is None else topic), response_callback)

    def remove_response_callback(self, topic, response_callback):
        """
        Removes a :class:`dxlclient.callbacks.ResponseCallback` from the client for the specified topic. This method
        must be invoked with the same arguments as when the callback was originally registered via
        :func:`add_response_callback`.

        :param topic: The topic to remove the callback for
        :param response_callback: The :class:`dxlclient.callbacks.ResponseCallback` to be removed for the specified topic
        """
        self._response_callbacks.remove_callback(("" if topic is None else topic), response_callback)

    def add_event_callback(self, topic, event_callback, subscribe_to_topic=True):
        """
        Adds a :class:`dxlclient.callbacks.EventCallback` to the client for the specified topic.
        The callback will be invoked when :class:`dxlclient.message.Event` messages are received by the client
        on the specified topic. A topic of ``None`` indicates that the callback should receive
        :class:`dxlclient.message.Event` messages for all topics (no filtering).

        :param topic: The topic to receive :class:`dxlclient.message.Event` messages on. A topic of ``None`` indicates
            that the callback should receive :class:`dxlclient.message.Event` messages for all topics (no filtering).
        :param event_callback: The :class:`dxlclient.callbacks.EventCallback` to be invoked when a
            :class:`dxlclient.message.Event` message is received on the specified topic
        :param subscribe_to_topic: Optional parameter to indicate if the client should subscribe
            (:func:`dxlclient.client.DxlClient.subscribe`) to the topic.
            By default the client will subscribe to the topic. Specify ``False`` to prevent subscribing to the topic.
        """
        self._event_callbacks.add_callback(("" if topic is None else topic), event_callback)
        if subscribe_to_topic is True and topic is not None:
            self.subscribe(topic)

    def remove_event_callback(self, topic, event_callback, unsubscribe_from_topic=True):
        """
        Removes a :class:`dxlclient.callbacks.EventCallback` from the client for the specified topic. This method
        must be invoked with the same arguments as when the callback was originally registered via
        :func:`add_event_callback`.

        :param topic: The topic to remove the callback for
        :param event_callback: The :class:`dxlclient.callbacks.EventCallback` to be removed for the specified topic
        :param unsubscribe_from_topic: Optional parameter to indicate if the client should also unsubscribe
            (:func:`dxlclient.client.DxlClient.unsubscribe`) from the topic. By default the client will unsubscribe
            from the topic. Specify ``False`` to prevent unsubscribing to the topic.
        """
        self._event_callbacks.remove_callback(("" if topic is None else topic), event_callback)
        if unsubscribe_from_topic is True and topic is not None:
            self.unsubscribe(topic)

    def _fire_request(self, request):
        """
        Fires the specified {@link Request} to {@link RequestCallback} listeners currently
        registered with the client.

        :param request: The {@link Request} to fire
        """
        self._request_callbacks.fire_message(request)

    def _fire_response(self, response):
        """
        Fires the specified {@link Response} to {@link ResponseCallback} listeners currently
        registered with the client.

        :param response: The {@link Response} to fire
        """
        self._response_callbacks.fire_message(response)

    def _fire_event(self, event):
        """
        Fires the specified {@link Event} to {@link EventCallback} listeners currently
        registered with the client.

        :param event: The {@link Event} to fire
        """
        self._event_callbacks.fire_message(event)

    def _handle_message(self, channel, payload):
        """
        Processes an incoming message. The bytes from the message are converted into the appropriate
        message type instance (request, response, event, etc.) and then the corresponding registered
        message callbacks are notified.

        :param channel: The channel that the message arrived on
        :param payload: The message received from the channel (as bytes)
        """
        message = Message._from_bytes(payload)
        message.destination_topic = channel

        if isinstance(message, Event):
            self._fire_event(message)
        elif isinstance(message, Request):
            self._fire_request(message)
        elif isinstance(message, (Response, ErrorResponse)):
            self._fire_response(message)
        else:
            raise ValueError("Unknown message type")

    def register_service_async(self, service_reg_info):
        """
        Registers a DXL service with the fabric asynchronously. The specified
        :class:`dxlclient.service.ServiceRegistrationInfo` instance contains information about the
        service that is to be registered.

        This method differs from :func:`register_service_sync` due to the fact that it returns to the caller
        immediately after sending the registration message to the DXL fabric (It does
        not wait for registration confirmation before returning).

        See :mod:`dxlclient.service` for more information on DXL services.

        :param service_reg_info: A :class:`dxlclient.service.ServiceRegistrationInfo` instance containing information
            about the service that is to be registered.
        """
        if self._service_manager:
            self._service_manager.add_service(service_reg_info)

    def unregister_service_async(self, service_reg_info):
        """
        Unregisters (removes) a DXL service with from the fabric asynchronously. The specified
        :class:`dxlclient.service.ServiceRegistrationInfo` instance contains information about the
        service that is to be removed.

        This method differs from :func:`unregister_service_sync` due to the fact that it returns to the caller
        immediately after sending the unregistration message to the DXL fabric (It does
        not wait for unregistration confirmation before returning).

        See :mod:`dxlclient.service` for more information on DXL services.

        :param service_reg_info: A :class:`dxlclient.service.ServiceRegistrationInfo` instance containing information
            about the service that is to be unregistered.
        """
        if self._service_manager:
            self._service_manager.remove_service(service_reg_info.service_id)

    def register_service_sync(self, service_req_info, timeout):
        """
        Registers a DXL service with the fabric. The specified
        :class:`dxlclient.service.ServiceRegistrationInfo` instance contains information about the
        service that is to be registered.

        This method will wait for confirmation of the service registration for up to the specified timeout
        in seconds. If the timeout is exceeded an exception will be raised.

        See :mod:`dxlclient.service` for more information on DXL services.

        :param service_reg_info: A :class:`dxlclient.service.ServiceRegistrationInfo` instance containing information
            about the service that is to be registered.
        :param timeout: The amount of time (in seconds) to wait for confirmation of the service registration.
            If the timeout is exceeded an exception will be raised.
        """
        if self._service_manager:
            if not self.connected:
                raise DxlException("Client is not currently connected")
            self._service_manager.add_service(service_req_info)
            service_req_info._wait_for_registration(timeout=timeout)

    def unregister_service_sync(self, service_req_info, timeout):
        """
        Unregisters (removes) a DXL service from the fabric. The specified
        :class:`dxlclient.service.ServiceRegistrationInfo` instance contains information about the
        service that is to be removed.

        This method will wait for confirmation of the service unregistration for up to the specified timeout
        in seconds. If the timeout is exceeded an exception will be raised.

        See :mod:`dxlclient.service` for more information on DXL services.

        :param service_reg_info: A :class:`dxlclient.service.ServiceRegistrationInfo` instance containing information
            about the service that is to be removed.
        :param timeout: The amount of time (in seconds) to wait for confirmation of the service unregistration.
            If the timeout is exceeded an exception will be raised.
        """
        if self._service_manager:
            if not self.connected:
                raise DxlException("Client is not currently connected")

            if not service_req_info:
                raise ValueError("Undefined service object")

            self._service_manager.remove_service(service_req_info.service_id)
            service_req_info._wait_for_unregistration(timeout=timeout)

    def _get_mqtt_client(self):
        """
        Returns the mqtt client instance
        :return: MQTT client instance
        """
        return mqtt.Client(client_id=self._config._client_id,
                           clean_session=True,
                           userdata=self,
                           protocol=mqtt.MQTTv311,
                           transport="websockets" if self.config.use_websockets else "tcp")

    def _set_mqtt_client_callbacks(self):
        """
        Sets the callbacks for MQTT client
        """
        # The MQTT client connect callback
        self._client.on_connect = _on_connect
        # The MQTT client disconnect callback
        self._client.on_disconnect = _on_disconnect
        # The MQTT client message callback
        self._client.on_message = _on_message
        # The MQTT client topic subscription callback
        self._client.on_subscribe = _on_subscribe
        # The MQTT client topic unsubscription callback
        self._client.on_unsubscribe = _on_unsubscribe
        # The MQTT client log callback
        if logger.isEnabledFor(logging.DEBUG):
            self._client.on_log = _on_log
