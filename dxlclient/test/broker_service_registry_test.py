""" Tests the broker service registry. """

import json
import threading

from nose.plugins.attrib import attr
from nose.tools import nottest
from dxlclient.test.base_test import BaseClientTest
from dxlclient import ErrorResponse, Request, Response
from dxlclient import RequestCallback, ServiceRegistrationInfo, UuidGenerator


# pylint: disable=missing-docstring

@attr('system')
class BrokerServiceRegistryTest(BaseClientTest):
    DXL_SERVICE_UNAVAILABLE_ERROR_CODE = 0x80000001
    DXL_SERVICE_UNAVAILABLE_ERROR_MESSAGE = \
        'unable to locate service for request'
    DXL_SERVICE_REGISTRY_QUERY_TOPIC = '/mcafee/service/dxl/svcregistry/query'
    MAX_WAIT = 5 * 60
    RESPONSE_WAIT = 60

    @staticmethod
    def normalized_error_code(error_response):
        return (0xFFFFFFFF + error_response.error_code + 1) \
            if error_response.error_code < 0 else error_response.error_code

    @nottest
    def register_test_service(self, client, service_type=None):
        topic = "broker_service_registry_test_service_" + \
                UuidGenerator.generate_id_as_string()
        reg_info = ServiceRegistrationInfo(
            client,
            service_type or "broker_service_registry_test_service_" +
            UuidGenerator.generate_id_as_string())
        callback = RequestCallback()
        callback.on_request = \
            lambda request: client.send_response(Response(request))
        reg_info.add_topic(topic, callback)
        client.register_service_sync(reg_info, self.DEFAULT_TIMEOUT)
        return reg_info

    def query_service_registry(self, client, query):
        request = Request(self.DXL_SERVICE_REGISTRY_QUERY_TOPIC)
        if not query:
            query = {}
        request.payload = json.dumps(query)
        response = client.sync_request(request, timeout=self.RESPONSE_WAIT)
        return json.loads(
            response.payload.decode("utf8").rstrip("\0"))["services"]

    def query_service_registry_by_service_id(self, client, service_id):
        response = self.query_service_registry(
            client, {"serviceId": service_id})
        return response[service_id] if service_id in response else None

    def query_service_registry_by_service_type(self, client, service_type):
        return self.query_service_registry(
            client, {"serviceType": service_type})

    def query_service_registry_by_service(self, client, service_reg_info):
        return self.query_service_registry_by_service_id(
            client, service_reg_info.service_id)

    #
    # Test querying the broker for services with a specific identifier.
    #
    @attr('system')
    def test_registry_query_by_id(self):
        with self.create_client() as client:
            client.connect()
            reg_info = self.register_test_service(client)
            # Validate that the service was initially registered with the
            # broker.
            self.assertIsNotNone(self.query_service_registry_by_service_id(
                client, reg_info.service_id))
            client.unregister_service_sync(reg_info, self.DEFAULT_TIMEOUT)
            # Validate that the broker unregistered the service after the
            # request made to the service failed.
            self.assertIsNone(self.query_service_registry_by_service_id(
                client, reg_info.service_id))

    #
    # Test querying the broker for services based on their type
    #
    @attr('system')
    def test_registry_query_by_type(self):
        with self.create_client() as client:
            client.connect()
            # Register two services (reg_info_1 and reg_info_2) with the same
            # service_type and one service (reg_info_3) with a different
            # service_type. When querying the registry using reg_info_1's
            # service_type, expect entries to be returned for reg_info_1 and
            # reg_info_2 but not reg_info_3 (since the service_type for the
            # latter would not match the query).
            reg_info_1 = self.register_test_service(client)
            reg_info_2 = self.register_test_service(client,
                                                    reg_info_1.service_type)
            reg_info_3 = self.register_test_service(client)
            services = self.query_service_registry_by_service_type(
                client, reg_info_1.service_type)
            self.assertIn(reg_info_1.service_id, services)
            self.assertIn(reg_info_2.service_id, services)
            self.assertNotIn(reg_info_3.service_id, services)

    #
    # Test round-robin for multiple services that support the same channel.
    #
    @attr('system')
    def test_round_robin_services(self):
        service_count = 10
        request_per_service_count = 10
        request_to_send_count = service_count * request_per_service_count

        request_received_count = [0]
        request_to_wrong_service_id_count = [0]
        requests_by_service = {}
        request_lock = threading.Lock()

        topic = UuidGenerator.generate_id_as_string()

        with self.create_client() as service_client:
            service_client.connect()

            def my_request(callback_service_id, request):
                with request_lock:
                    request_received_count[0] += 1
                    if request.service_id and \
                            (request.service_id != callback_service_id):
                        request_to_wrong_service_id_count[0] += 1
                    if request.service_id in requests_by_service:
                        requests_by_service[request.service_id] += 1
                    else:
                        requests_by_service[request.service_id] = 1
                    response = Response(request)
                    service_client.send_response(response)

            def create_service_reg_info():
                reg_info = ServiceRegistrationInfo(service_client,
                                                   "round_robin_service")
                callback = RequestCallback()
                callback.on_request = \
                    lambda request: my_request(reg_info.service_id, request)
                reg_info.add_topic(topic, callback)
                service_client.register_service_sync(reg_info,
                                                     self.DEFAULT_TIMEOUT)
                return reg_info

            reg_infos = [create_service_reg_info() # pylint: disable=unused-variable
                         for _ in range(service_count)]
            with self.create_client() as request_client:
                request_client.connect()
                for _ in range(0, request_to_send_count):
                    request = Request(topic)
                    response = request_client.sync_request(
                        request, timeout=self.RESPONSE_WAIT)
                    self.assertNotIsInstance(response, ErrorResponse)
                    self.assertEqual(request.message_id,
                                     response.request_message_id)
            with request_lock:
                self.assertEqual(0, request_to_wrong_service_id_count[0])
                self.assertEqual(request_to_send_count,
                                 request_received_count[0])
                self.assertEqual(service_count, len(requests_by_service))
                for service_request_count in requests_by_service.values():
                    self.assertEqual(request_per_service_count,
                                     service_request_count)

    #
    # Test routing requests to multiple services.
    #
    @attr('system')
    def test_multiple_services(self):
        with self.create_client() as service_client:
            service_client.connect()
            reg_info_topic_1 = "multiple_services_test_1_" + \
                               UuidGenerator.generate_id_as_string()
            reg_info_1 = ServiceRegistrationInfo(
                service_client, "multiple_services_test_1")

            def reg_info_request_1(request):
                response = Response(request)
                response.payload = "service1"
                service_client.send_response(response)

            reg_info_callback_1 = RequestCallback()
            reg_info_callback_1.on_request = reg_info_request_1
            reg_info_1.add_topic(reg_info_topic_1, reg_info_callback_1)
            service_client.register_service_sync(reg_info_1,
                                                 self.DEFAULT_TIMEOUT)

            reg_info_topic_2 = "multiple_services_test_2_" + \
                               UuidGenerator.generate_id_as_string()
            reg_info_2 = ServiceRegistrationInfo(
                service_client, "multiple_services_test_2")

            def reg_info_request_2(request):
                response = Response(request)
                response.payload = "service2"
                service_client.send_response(response)

            reg_info_callback_2 = RequestCallback()
            reg_info_callback_2.on_request = reg_info_request_2
            reg_info_2.add_topic(reg_info_topic_2, reg_info_callback_2)
            service_client.register_service_sync(reg_info_2,
                                                 self.DEFAULT_TIMEOUT)
            with self.create_client() as request_client:
                request_client.connect()
                response = request_client.sync_request(
                    Request(reg_info_topic_1), self.DEFAULT_TIMEOUT)
                self.assertIsInstance(response, Response)
                self.assertEqual(response.payload.decode("utf8"), "service1")
                response = request_client.sync_request(
                    Request(reg_info_topic_2), self.DEFAULT_TIMEOUT)
                self.assertIsInstance(response, Response)
                self.assertEqual(response.payload.decode("utf8"), "service2")

    #
    # Test circumventing round-robin of services by specifying a single service
    # instance in the request.
    #
    @attr('system')
    def test_specify_service_in_request(self):
        service_count = 10
        request_count = 100

        request_received_count = [0]
        request_to_wrong_service_id_count = [0]
        requests_by_service = {}
        request_lock = threading.Lock()

        topic = UuidGenerator.generate_id_as_string()

        with self.create_client() as service_client:
            service_client.connect()

            def my_request(callback_service_id, request):
                with request_lock:
                    request_received_count[0] += 1
                    if request.service_id and \
                            (request.service_id != callback_service_id):
                        request_to_wrong_service_id_count[0] += 1
                    if request.service_id in requests_by_service:
                        requests_by_service[request.service_id] += 1
                    else:
                        requests_by_service[request.service_id] = 1
                    response = Response(request)
                    service_client.send_response(response)

            def create_service_reg_info():
                reg_info = ServiceRegistrationInfo(
                    service_client, "registry_specified_service_id_test")
                callback = RequestCallback()
                callback.on_request = \
                    lambda request: my_request(reg_info.service_id, request)
                reg_info.add_topic(topic, callback)
                service_client.register_service_sync(reg_info,
                                                     self.DEFAULT_TIMEOUT)
                return reg_info

            reg_infos = [create_service_reg_info()
                         for _ in range(service_count)]
            with self.create_client() as request_client:
                request_client.connect()
                for _ in range(0, request_count):
                    request = Request(topic)
                    request.service_id = reg_infos[0].service_id
                    response = request_client.sync_request(
                        request, timeout=self.RESPONSE_WAIT)
                    self.assertNotIsInstance(response, ErrorResponse)
                    self.assertEqual(request.message_id,
                                     response.request_message_id)
            with request_lock:
                self.assertEqual(0, request_to_wrong_service_id_count[0])
                self.assertEqual(request_count, request_received_count[0])
                self.assertEqual(1, len(requests_by_service))
                self.assertIn(reg_infos[0].service_id, requests_by_service)
                self.assertEqual(
                    request_count, requests_by_service[reg_infos[0].service_id])

    #
    # Test registering and unregistering the same service
    #
    @attr('system')
    def test_multiple_registrations(self):
        service_registration_count = 10
        request_received_count = [0]

        topic = UuidGenerator.generate_id_as_string()

        with self.create_client() as service_client:
            service_client.connect()

            def my_request(request):
                request_received_count[0] += 1
                response = Response(request)
                service_client.send_response(response)

            reg_info = ServiceRegistrationInfo(service_client,
                                               "multiple_registrations_test")
            callback = RequestCallback()
            callback.on_request = my_request
            reg_info.add_topic(topic, callback)
            with self.create_client() as request_client:
                request_client.connect()
                for _ in range(0, service_registration_count):
                    service_client.register_service_sync(reg_info,
                                                         self.DEFAULT_TIMEOUT)
                    request = Request(topic)
                    response = request_client.sync_request(
                        request, timeout=self.RESPONSE_WAIT)
                    self.assertNotIsInstance(response, ErrorResponse)
                    self.assertEqual(request.message_id,
                                     response.request_message_id)
                    service_client.unregister_service_sync(reg_info,
                                                           self.DEFAULT_TIMEOUT)
                self.assertEqual(service_registration_count,
                                 request_received_count[0])

    #
    # Test the state of the response when no channel is registered with the
    # broker for a service.
    #
    @attr('system')
    def test_response_service_not_found_no_channel(self):
        request_received = [False]

        topic = UuidGenerator.generate_id_as_string()

        with self.create_client() as service_client:
            service_client.connect()

            def my_request(request):
                request_received[0] = True
                service_client.send_response(Response(request))

            reg_info = ServiceRegistrationInfo(
                service_client, "response_service_not_found_no_channel_test")
            callback = RequestCallback()
            callback.on_request = my_request
            reg_info.add_topic(topic, callback)
            service_client.register_service_sync(reg_info,
                                                 self.DEFAULT_TIMEOUT)
            service_client.unsubscribe(topic)
            self.assertIsNotNone(
                self.query_service_registry_by_service(
                    service_client, reg_info))
            with self.create_client() as request_client:
                request_client.connect()
                request = Request(topic)
                response = request_client.sync_request(
                    request, timeout=self.RESPONSE_WAIT)
                self.assertFalse(request_received[0])
                self.assertIsInstance(response, ErrorResponse)
                self.assertEqual(reg_info.service_id, response.service_id)
                self.assertEqual(
                    self.DXL_SERVICE_UNAVAILABLE_ERROR_CODE,
                    BrokerServiceRegistryTest.normalized_error_code(response))
                self.assertEqual(self.DXL_SERVICE_UNAVAILABLE_ERROR_MESSAGE,
                                 response.error_message)
                self.assertIsNone(self.query_service_registry_by_service(
                    service_client, reg_info))

    #
    # Test the state of the response when the broker routes a service request
    # to a client which has no matching service id registered.
    #
    @attr('system')
    def test_response_service_not_found_no_service_id_at_client(self):
        request_received = [False]

        topic = UuidGenerator.generate_id_as_string()

        with self.create_client() as service_client:
            service_client.connect()

            def my_request(request):
                request_received[0] = True
                service_client.send_response(Response(request))

            reg_info = ServiceRegistrationInfo(
                service_client,
                "response_service_not_found_no_service_id_at_client_test")
            callback = RequestCallback()
            callback.on_request = my_request
            reg_info.add_topic(topic, callback)
            reg_info.add_topic(topic, callback)
            service_client.register_service_sync(reg_info,
                                                 self.DEFAULT_TIMEOUT)
            self.assertIsNotNone(
                self.query_service_registry_by_service(
                    service_client, reg_info))
            with self.create_client() as request_client:
                request_client.connect()
                # Remove the service's registration with the client-side
                # ServiceManager, avoiding unregistration of the service from
                # the broker. This should allow the broker to forward the
                # request on to the service client.
                registered_services = service_client._service_manager.services
                service = registered_services[reg_info.service_id]
                del registered_services[reg_info.service_id]
                request = Request(topic)
                response = request_client.sync_request(
                    request, timeout=self.RESPONSE_WAIT)
                # Re-register the service with the internal ServiceManager so
                # that its resources (TTL timeout, etc.) can be cleaned up
                # properly at shutdown.
                registered_services[reg_info.service_id] = service
                # The request should receive an 'unavailable service' error
                # response because the service client should be unable to route
                # the request to an internally registered service.
                self.assertFalse(request_received[0])
                self.assertIsInstance(response, ErrorResponse)
                self.assertEqual(reg_info.service_id, response.service_id)
                self.assertEqual(
                    self.DXL_SERVICE_UNAVAILABLE_ERROR_CODE,
                    BrokerServiceRegistryTest.normalized_error_code(response))
                self.assertEqual(self.DXL_SERVICE_UNAVAILABLE_ERROR_MESSAGE,
                                 response.error_message)
                self.assertIsNone(self.query_service_registry_by_service(
                    service_client, reg_info))
