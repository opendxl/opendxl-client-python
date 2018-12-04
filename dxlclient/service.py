# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
################################################################################

""" Classes used for registering and exposing services to a DXL fabric. """

from __future__ import absolute_import
import json
import logging
from threading import Timer, Condition, RLock
import time

from dxlclient import _BaseObject
from dxlclient._callback_manager import _RequestCallbackManager
from dxlclient._uuid_generator import UuidGenerator
from dxlclient.callbacks import RequestCallback
from dxlclient.exceptions import DxlException
from dxlclient.message import Message, Request, ErrorResponse

from ._compat import is_string, iter_dict_items

logger = logging.getLogger(__name__)


class ServiceRegistrationInfo(_BaseObject):
    """
    Service Registration instances are used to register and expose services onto a DXL fabric.

    DXL Services are exposed to the DXL fabric and are invoked in a fashion similar to RESTful web services.
    Communication between an invoking client and the DXL service is one-to-one (request/response).

    Each service is identified by the "topics" it responds to. Each of these "topics" can be thought of as
    a method that is being "invoked" on the service by the remote client.

    Multiple service "instances" can be registered with the DXL fabric that respond to the same "topics". When
    this occurs (unless explicitly overridden by the client) the fabric will select the particular instance
    to route the request to (by default round-robin). Multiple service instances can be used to increase
    scalability and fault-tolerance.

    The following demonstrates registering a service that responds to a single topic with the DXL fabric:

    .. code-block:: python

        from dxlclient.callbacks import RequestCallback
        from dxlclient.message import Response
        from dxlclient.service import ServiceRegistrationInfo

        class MyRequestCallback(RequestCallback):
            def on_request(self, request):
                # Extract information from request
                print request.payload.decode()

                # Create the response message
                res = Response(request)

                # Populate the response payload
                res.payload = "pong".encode()

                # Send the response
                dxl_client.send_response(res)

        # Create service registration object
        info = ServiceRegistrationInfo(dxl_client, "/mycompany/myservice")

        # Add a topic for the service to respond to
        info.add_topic("/testservice/testrequesttopic", MyRequestCallback())

        # Register the service with the fabric (wait up to 10 seconds for registration to complete)
        dxl_client.register_service_sync(info, 10)

    The following demonstrates a client that is invoking the service in the example above:

    .. code-block:: python

        from dxlclient.message import Request, Message

        # Create the request message
        req = Request("/testservice/testrequesttopic")

        # Populate the request payload
        req.payload = "ping".encode()

        # Send the request and wait for a response (synchronous)
        res = dxl_client.sync_request(req)

        # Extract information from the response (if an error did not occur)
        if res.message_type != Message.MESSAGE_TYPE_ERROR:
            print res.payload.decode()
    """

    def __init__(self, client, service_type):
        """
        Constructor parameters:

        :param client: The :class:`dxlclient.client.DxlClient` instance that will expose this service
        :param service_type: A textual name for the service. For example, "/mycompany/myservice"
        """
        super(ServiceRegistrationInfo, self).__init__()

        # if not isinstance(channels, list):
        # raise ValueError('Channels should be a list')
        # if not channels:
        #     raise InvalidServiceException('Channel list is empty')
        if not service_type:
            raise ValueError("Undefined service name")

            #The service type or name prefix
        self._service_type = service_type
        # The unique service ID
        self._service_id = UuidGenerator.generate_id_as_string()

        # The map of registered channels and their associated callbacks
        self._callbacks_by_topic = {}
        #The map of meta data associated with this service (name-value pairs)
        self._metadata = {}
        # List of destination tenants
        self._destination_tenant_guids = []

        # The Time-To-Live (TTL) of the service registration (default: 60 minutes)
        self._ttl = 60  # minutes
        # The minimum Time-To-Live (TTL) of the service registration (default: 10 minutes)
        self._ttl_lower_limit = 10

        # Internal client reference
        self._dxl_client = client

        # Registration sync object
        self._registration_sync = Condition()

        # Whether at least one registration has occurred
        self._registration_occurred = False

        # Whether at least one unregistration registration has occurred
        self._unregistration_occurred = False

        self._destroy_lock = RLock()
        self._destroyed = False

    def __del__(self):
        """destructor"""
        super(ServiceRegistrationInfo, self).__del__()
        self._destroy()

    def _destroy(self, unregister=True):
        """
        Destroys the service registration

        :param unregister: Whether to unregister the service from the fabric
        """
        with self._destroy_lock:
            if not self._destroyed:
                if unregister and self._dxl_client:
                    try:
                        self._dxl_client.unregister_service_async(self)
                    except Exception: # pylint: disable=broad-except
                        # Currently ignoring this as it can occur due to the fact that we are
                        # attempting to unregister a service that was never registered
                        pass
                self._dxl_client = None
                self._destroyed = True

    @property
    def service_type(self):
        """
        A textual name for the service. For example, "/mycompany/myservice"
        """
        return self._service_type

    @property
    def service_id(self):
        """
        A unique identifier for the service instance (automatically generated when the :class:`ServiceRegistrationInfo`
        object is constructed)
        """
        return self._service_id

    @property
    def metadata(self):
        """
        A dictionary of name-value pairs that are sent as part of the service registration. Brokers provide
        a registry service that allows for registered services and their associated meta-information to be inspected.
        The metadata is typically used to include information such as the versions for products that are
        exposing DXL services, etc.
        """
        return self._metadata

    @metadata.setter
    def metadata(self, metadata):
        self._metadata = metadata

    @property
    def ttl(self):
        """
        The interval (in minutes) at which the client will automatically re-register the service with the
        DXL fabric (defaults to 60 minutes)
        """
        return self._ttl

    @ttl.setter
    def ttl(self, ttl):
        self._ttl = ttl

    @property
    def topics(self):
        """
        Returns a tuple containing the topics that the service responds to
        """
        return tuple(self._callbacks_by_topic.keys())

    def add_topic(self, topic, callback):
        """
        Registers a topic for the service to respond to along with the :class:`dxlclient.callbacks.RequestCallback`
        that will be invoked.

        :param topic:  The topic for the service to respond to
        :param callback: The :class:`dxlclient.callbacks.RequestCallback` that will be invoked when a
            :class:`dxlclient.message.Request` message is received
        """
        # TODO: use dictionary get method
        try:
            callbacks = self._callbacks_by_topic[topic]
        except KeyError:
            callbacks = set()
            self._callbacks_by_topic[topic] = callbacks
        finally:
            callbacks.add(callback)

    def add_topics(self, callbacks_by_topic):
        """
        Registers a set of topics for the service to respond to along with their associated
        :class:`dxlclient.callbacks.RequestCallback` instances as a dictionary

        :param callbacks_by_topic: Dictionary containing a set of topics for the service to respond to along with
            their associated :class:`dxlclient.callbacks.RequestCallback` instances
        """
        if not isinstance(callbacks_by_topic, dict):
            raise ValueError("Channel and callback should be a dictionary")
        if not callbacks_by_topic:
            raise ValueError("Undefined channel")
        for channel, callback in iter_dict_items(callbacks_by_topic):
            self.add_topic(channel, callback)

    @property
    def destination_tenant_guids(self):
        """
        The set of tenant identifiers that the service will be available to. Setting this value will limit
        which tenants can invoke the service.
        """
        return self._destination_tenant_guids

    @destination_tenant_guids.setter
    def destination_tenant_guids(self, tenant_guids=None):
        if tenant_guids is None:
            tenant_guids = []
        self._destination_tenant_guids = tenant_guids

    def _wait_for_registration_notification(self, wait_time):
        """
        Waits for a registration notification (register or unregister).

        :param waitTime:   The amount of time to wait.
        :return: None.
        """
        with self._registration_sync:
            if wait_time > 0:
                self._registration_sync.wait(wait_time)
            else:
                raise DxlException("Timeout waiting for service related notification")

    def _wait_for_registration(self, timeout):
        """
        Waits for the service to be registered with the broker for the first time.

        :param timeout: The amount of time to wait for the registration to occur.
        :return: None.
        """
        with self._registration_sync:
            end_time = int(time.time()) + timeout
            while not self._registration_occurred:
                self._wait_for_registration_notification(end_time - int(time.time()))

    def _notify_registration_succeeded(self):
        """
        Invoked when the service has been successfully registered with a broker.

        :return: None.
        """
        with self._registration_sync:
            self._registration_occurred = True
            self._unregistration_occurred = False
            self._registration_sync.notify_all()

    # @synchronized
    def _wait_for_unregistration(self, timeout):
        """
        Waits for the service to be unregistered with the broker for the first time.

        :param timeout: The amount of time to wait for the unregistration to occur.
        :return: None.
        """
        end_time = int(time.time()) + timeout
        with self._registration_sync:
            while not self._unregistration_occurred:
                self._wait_for_registration_notification(end_time - int(time.time()))

    #@synchronized
    def _notify_unregistration_succeeded(self):
        """
        Invoked when the service has been successfully unregistered with a broker.

        :return: None.
        """
        with self._registration_sync:
            self._registration_occurred = False
            self._unregistration_occurred = True
            self._registration_sync.notify_all()


class _ServiceRegistrationHandler(_BaseObject):
    def __init__(self, client, service):
        """
        Constructs the ServiceRegistrationHandler object.

        :param client:  The internal client reference.
        :param service: The service registration info.
        :return: None.
        """
        super(_ServiceRegistrationHandler, self).__init__()

        # The service type or name prefix
        self.service_type = service.service_type
        # The service instance ID
        self.instance_id = service.service_id
        # The list of full qualified registered channels
        self.channels = service.topics
        # The map of meta data associated with this service (name-value pairs)
        self.metadata = service.metadata.copy()
        # The Time-To-Live (TTL) grace period of the service registration (default: 10 minutes)
        self.ttl_grace_period = 10
        # The service registration info */
        self.service = service
        # The internal client reference */
        self.client = client
        # The request callback manager */
        self.request_callbacks = _RequestCallbackManager()
        self.deleted = False
        self.ttl_timer = None
        self.register_time = 0
        self.ttl = service.ttl
        self.lock = RLock()

        self._destroy_lock = RLock()
        self._destroyed = False

        service_ref = self.service
        if not service_ref:
            raise DxlException("Service no longer valid")

        for channel, callbacks in iter_dict_items(service_ref._callbacks_by_topic):
            for callback in callbacks:
                self.request_callbacks.add_callback(channel, callback)

    def __del__(self):
        """destructor"""
        super(_ServiceRegistrationHandler, self).__del__()
        self.destroy()

    def destroy(self, unregister=True):
        """
        Destroys the service registration

        :param unregister: Whether to unregister the service from the fabric
        """
        with self._destroy_lock:
            if not self._destroyed:
                info = self.service
                if info:
                    for channel, callbacks in iter_dict_items(info._callbacks_by_topic):
                        for callback in callbacks:
                            self.request_callbacks.remove_callback(channel, callback)
                    info._destroy(unregister)
                self.client = None
                self._destroyed = True

    def send_register_service_request(self):
        """
        Send the registration request for the service.

        :return: None.
        """
        if not self.client:
            raise DxlException("Client not defined")
        with self.lock:
            req = Request(destination_topic=_ServiceManager.DXL_SERVICE_REGISTER_REQUEST_CHANNEL)
            req.payload = self.json_register_service()
            req.destination_tenant_guids = self.service.destination_tenant_guids
            response = self.client.sync_request(req, timeout=10)
            if response.message_type != Message.MESSAGE_TYPE_ERROR:
                self.update_register_time()
                info = self.service
                if info:
                    info._notify_registration_succeeded()
            else:
                # TODO: Notify the client with an exception if an error occurred, so that it doesn't wait for timeout
                logger.error("Error registering service.")

    def send_unregister_service_event(self):
        """
        Send the unregister event for the service.

        :return: None.
        """
        if not self.client:
            raise DxlException("Client not defined")
        with self.lock:
            # Send the unregister event only if the register event was sent before and TTL has not yet expired.
            current_time = int(time.time())
            last_register_time = self.get_register_time()

            if last_register_time > 0 and (current_time - last_register_time) <= (self.ttl * 60):
                request = Request(destination_topic=_ServiceManager.DXL_SERVICE_UNREGISTER_REQUEST_CHANNEL)
                request.payload = self.json_unregister_service()
                response = self.client.sync_request(request, timeout=60)
                if response.message_type == Message.MESSAGE_TYPE_ERROR:
                    raise DxlException("Unregister service request timed out")
            else:
                if last_register_time > 0:
                    # pylint: disable=logging-not-lazy
                    logger.info(
                        "TTL expired, unregister service event omitted for " +
                        self.service_type + " (" + self.instance_id +
                        ")")
            info = self.service
            if info:
                info._notify_unregistration_succeeded()

    def get_register_time(self):
        """
        Returns the last registration time in milliseconds.

        :return The last registration time in milliseconds, or 0L if not registered.
        """
        with self.lock:
            return self.register_time

    def update_register_time(self):
        """
        Updates the last registration time in milliseconds.

        :return: None.
        """
        with self.lock:
            self.register_time = int(time.time())

    def mark_for_deletion(self):
        """
        Marks the service for deletion.

        :return: None.
        """
        self.deleted = True

    def is_deleted(self):
        """
        Returns true if the service is marked for deletion.

        :return True if the service is marked for deletion, otherwise false.
        """
        return self.deleted

    def _timer_callback(self):
        """Callback invoked by the timer task (to re-register the service"""
        if self.client.connected:
            with self.lock:
                # Send unregister event if service marked for deletion or is no
                # longer valid
                if self.deleted:
                    self.mark_for_deletion()
                    self.send_unregister_service_event()
                    self.ttl_timer.cancel()
                else:
                    self.send_register_service_request()
                    self.ttl_timer = Timer(self.ttl * 60, self._timer_callback)
                    self.ttl_timer.daemon = True
                    self.ttl_timer.start()
        else:
            if self.ttl_timer:
                self.ttl_timer.cancel()

    def start_timer(self):
        """
        Starts the TTL timer task.

        :return: None.
        """
        if not self.client:
            raise DxlException("Client not defined")

        if self.client.connected and not self.deleted:
            self.ttl_timer = Timer(0, self._timer_callback)
            self.ttl_timer.daemon = True
            self.ttl_timer.start()

    def stop_timer(self):
        """
        Stops the TTL timer task.

        :return: None.
        """
        if self.ttl_timer:
            self.ttl_timer.cancel()
            self.ttl_timer = None

    def json_register_service(self):  # instanceId or service guid?
        """
        Formats the JSON payload to be sent in a service registration request
        to the broker.

        :return: The request payload.
        """
        return json.dumps({
            'serviceType': self.service_type,
            'metaData': self.metadata,
            'requestChannels': list(self.channels),
            'ttlMins': self.ttl,
            'serviceGuid': self.instance_id
        })

    def json_unregister_service(self):
        """
        Formats the JSON payload to be sent in a service unregistration request
        to the broker.

        :return: The request payload.
        """
        return json.dumps({
            'serviceGuid': self.instance_id
        })


# pylint: disable= invalid-name
class _ServiceManager(RequestCallback):
    DXL_SERVICE_UNREGISTER_REQUEST_CHANNEL = "/mcafee/service/dxl/svcregistry/unregister"
    # The channel notified when services are registered
    DXL_SERVICE_REGISTER_CHANNEL = "/mcafee/event/dxl/svcregistry/register"
    # The channel to publish a service registration request to
    DXL_SERVICE_REGISTER_REQUEST_CHANNEL = "/mcafee/service/dxl/svcregistry/register"
    # The channel notified when services are unregistered
    DXL_SERVICE_UNREGISTER_CHANNEL = "/mcafee/event/dxl/svcregistry/unregister"

    def __init__(self, client):
        """
        Creates the service manager.

        :param client: client that the service manager is associated with.
        :return: None.
        """
        super(_ServiceManager, self).__init__()

        # if not isinstance(client, DxlClient):
        #     raise ValueError("Expected DxlClient object")
        self.__client = client
        #Map containing registered services */
        self.services = {}

        self.lock = RLock()

    def destroy(self):
        """Destroys the service manager (releases resources)"""
        with self.lock:
            for key in list(self.services.keys()):
                self.remove_service(key)
            self.__client = None

    def add_service(self, service_reg_info):
        """
        Adds the specified service.

        :param service: The service to add.
        :return: None.
        """
        if not isinstance(service_reg_info, (type, ServiceRegistrationInfo)):
            raise ValueError("Expected ServiceRegistrationInfo object")

        with self.lock:
            try:
                service_handler = self.services[service_reg_info._service_id]
                raise DxlException("Service already registered")
            except KeyError:
                pass

            # Add service to registry
            service_handler = _ServiceRegistrationHandler(self.__client, service_reg_info)
            # Add the new service handler into a copy of self.services. This
            # avoids causing issues with any readers using the current value of
            # the object.
            services = self.services.copy()
            services[service_reg_info._service_id] = service_handler

            # Subscribe channels
            for channel in service_reg_info.topics:
                self.__client.subscribe(channel)
                self.__client.add_request_callback(channel, self)

            if self.__client.connected:
                service_handler.start_timer()

            self.services = services

    def remove_service(self, service_id):
        """
        Removes the specified service.

        :param instanceId: The instance ID of the service to remove.
        :return: None.
        """
        if not is_string(service_id):
            raise ValueError("Expected service id")

        if not service_id:
            raise ValueError("Invalid service id")

        with self.lock:
            service_handler = self.services.get(service_id, None)
            if not service_handler:
                raise DxlException("Service instance ID unknown: " + str(service_id))

            service_handler.stop_timer()

            for channel in service_handler.channels:
                self.__client.unsubscribe(channel)
                self.__client.remove_request_callback(channel, self)

            service_handler.mark_for_deletion()

            #If the client is actually connected, send unregister event. Remove upon success.
            if self.__client.connected:
                try:
                    service_handler.send_unregister_service_event()
                except Exception as ex: # pylint: disable=broad-except
                    logger.error(
                        "Error sending unregister service event for %s (%s): %s",
                        service_handler.service_type,
                        service_handler.instance_id,
                        ex)

            # Remove the service handler from a copy of self.services. This
            # avoids causing issues with any readers using the current value of
            # the object.
            services = self.services.copy()
            del services[service_id]
            service_handler.destroy(unregister=False)
            self.services = services

    def on_request(self, request):
        """
        Invoked when a {@link Request} has been received.

        :param request: The request.
        :return: None.
        """
        # Store the current value of self.services in a local variable before
        # accessing its contents. This should ensure that if
        # self.callbacks_by_channel is reassigned after the lock is released
        # that no concurrent modification errors are encountered.
        services = self.services
        service_instance_id = request.service_id
        if not service_instance_id:
            for service_id in services:
                self._on_request(services[service_id], request)
        else:
            service_registration_handler = services.get(service_instance_id)
            if service_registration_handler:
                self._on_request(service_registration_handler, request)
            else:
                logger.warning(
                    "No service with GUID %s registered. Ignoring request.",
                    service_instance_id)
                self.send_service_not_found_error_message(request)

    def send_service_not_found_error_message(self, request):
        """
        Sends a service not found error message response.

        :param request: The request.
        :return: None.
        """
        # todo: error code via constants
        error_response = ErrorResponse(request=request, error_code=0x80000001,
                                       error_message="unable to locate service for request")

        try:
            self.__client.send_response(error_response)
        except Exception as ex: # pylint: disable=broad-except
            logger.error(
                "Error sending service not found error message: %s", ex)

    @staticmethod
    def _on_request(service_handler, request):
        service_handler.request_callbacks.fire_message(request)

    def on_connect(self):
        """
        On connect, check for deleted and/or rogue services and send unregister event, if necessary.
        Start timer threads for all active services.

        :return: None
        """
        with self.lock:
            services = {}
            for service_id in self.services:
                service_handler = self.services[service_id]
                if service_handler.is_deleted():
                    try:
                        service_handler.send_unregister_service_event()
                    except Exception as ex: # pylint: disable=broad-except
                        logger.error(
                            "Error sending unregister service event for %s (%s): %s",
                            service_handler.service_type,
                            service_handler.instance_id,
                            ex)
                else:
                    services[service_id] = service_handler
                    try:
                        service_handler.start_timer()
                    except Exception as ex: # pylint: disable=broad-except
                        logger.error(
                            "Failed to start timer thread for service %s (%s): %s",
                            service_handler.service_type,
                            service_handler.instance_id,
                            ex)
            self.services = services

    def on_disconnect(self):
        """
        On disconnect, send unregister event for all active services as long as still connected.
        Stop all timer threads.

        :return: None.
        """
        with self.lock:
            for service_id in self.services:
                service_handler = self.services[service_id]
                if self.__client.connected:
                    try:
                        service_handler.send_unregister_service_event()
                    except Exception as ex: # pylint: disable=broad-except
                        logger.error(
                            "Error sending unregister service event for %s (%s): %s",
                            service_handler.service_type,
                            service_handler.instance_id,
                            ex)
                service_handler.stop_timer()
