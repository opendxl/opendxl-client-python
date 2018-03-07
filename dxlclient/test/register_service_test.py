""" Tests the service registration methods of the DxlClient. """

from __future__ import absolute_import
from __future__ import print_function
import time
import logging
import threading
import gc
import json
from nose.plugins.attrib import attr
from dxlclient import DxlException, ErrorResponse, EventCallback, Request
from dxlclient import RequestCallback, Response, ServiceRegistrationInfo
from dxlclient.service import _ServiceManager
from dxlclient.exceptions import WaitTimeoutException
from .base_test import BaseClientTest

# pylint: disable=missing-docstring, too-many-locals


@attr('system')
class RegisterServiceClientTest(BaseClientTest):
    SERVICE_REF_CLEANUP_DELAY = 30

    info = None
    info_registered = False
    info_registrations = 0
    info_unregistrations = 0

    def add_client_callbacks(self, client, on_client_request_callback=None):
        request_callback = RequestCallback()

        def on_request(request):
            logging.info(request.destination_topic)
            logging.info(request.payload)

            if on_client_request_callback:
                on_client_request_callback()
            response = Response(request)
            response.payload = "Ok"
            try:
                client.send_response(response)
            except DxlException as ex:
                print("Failed to send response" + str(ex))

        request_callback.on_request = on_request

        self.info = ServiceRegistrationInfo(client, "/mcafee/service/JTI")
        self.info_registered = False
        self.info_registrations = 0
        self.info_unregistrations = 0

        service_id = self.info.service_id
        self.info.add_topic("/mcafee/service/JTI/file/reputation/" +
                            service_id, request_callback)
        self.info.add_topic("/mcafee/service/JTI/cert/reputation/" +
                            service_id, request_callback)

        def is_event_for_service(event):
            return json.loads(event.payload.decode(
                "utf8").rstrip("\0"))["serviceGuid"] == service_id

        class ServiceRegisteredCallback(EventCallback):
            def __init__(self, test):
                self.test = test
                super(ServiceRegisteredCallback, self).__init__()

            def on_event(self, event):
                if is_event_for_service(event):
                    self.test.info_registrations += 1
                    self.test.info_registered = True

        class ServiceUnregisteredCallback(EventCallback):
            def __init__(self, test):
                self.test = test
                super(ServiceUnregisteredCallback, self).__init__()

            def on_event(self, event):
                if is_event_for_service(event):
                    self.test.info_unregistrations += 1
                    self.test.info_registered = False

        client.add_event_callback(_ServiceManager.DXL_SERVICE_REGISTER_CHANNEL,
                                  ServiceRegisteredCallback(self))
        client.add_event_callback(
            _ServiceManager.DXL_SERVICE_UNREGISTER_CHANNEL,
            ServiceUnregisteredCallback(self))

    def wait_info_registered_state(self, new_register_state):
        start = time.time()
        while (self.info_registered != new_register_state) and \
                (time.time() - start < self.REG_DELAY):
            if self.info_registered != new_register_state:
                time.sleep(0.1)
        return self.info_registered

    def wait_info_registered(self):
        return self.wait_info_registered_state(True)

    def wait_info_not_registered(self):
        return not self.wait_info_registered_state(False)

    @staticmethod
    def service_ref_valid(client, service_id):
        services = client._service_manager.services
        return service_id in services and \
               services[service_id].get_service() is not None

    def wait_for_service_reference_to_be_freed(self, client, service_id):
        start = time.time()
        while self.service_ref_valid(client, service_id) and \
                (time.time() - start < self.SERVICE_REF_CLEANUP_DELAY):
            time.sleep(0.1)
        return not self.service_ref_valid(client, service_id)

    @attr('system')
    def test_register_service_before_connect(self):
        with self.create_client() as client:
            self.add_client_callbacks(client)
            client.register_service_async(self.info)
            client.connect()
            self.assertTrue(self.wait_info_registered())
            client.unregister_service_sync(self.info, self.REG_DELAY)
            self.assertTrue(self.wait_info_not_registered())

            self.assertEqual(1, self.info_registrations)
            self.assertEqual(1, self.info_unregistrations)

    @attr('system')
    def test_register_service_after_connect(self):

        with self.create_client() as client:
            self.add_client_callbacks(client)
            client.connect()

            client.register_service_sync(self.info, self.REG_DELAY)
            self.assertTrue(self.wait_info_registered())

            client.unregister_service_sync(self.info, self.REG_DELAY)
            self.assertTrue(self.wait_info_not_registered())

            self.assertEqual(1, self.info_registrations)
            self.assertEqual(1, self.info_unregistrations)

    @attr('system')
    def test_register_service_never_connect(self):

        with self.create_client() as client:
            self.add_client_callbacks(client)
            client.register_service_async(self.info)
            client.unregister_service_async(self.info)

            self.assertEqual(0, self.info_registrations)
            self.assertEqual(0, self.info_unregistrations)

    @attr('system')
    def test_register_unregister_service_before_connect(self):
        with self.create_client() as client:
            self.add_client_callbacks(client)
            client.register_service_async(self.info)
            client.unregister_service_async(self.info)
            client.connect()

            self.assertEqual(0, self.info_registrations)
            self.assertEqual(0, self.info_unregistrations)

    @attr('system')
    def test_register_service_and_send_request(self):

        with self.create_client() as client:
            self.add_client_callbacks(client)
            client.register_service_async(self.info)
            client.connect()
            self.assertTrue(self.wait_info_registered())

            request = Request("/mcafee/service/JTI/file/reputation/" +
                              self.info.service_id)
            request.payload = "Test"

            response = client.sync_request(request, self.POST_OP_DELAY)
            logging.info("Response payload: %s",
                         response.payload.decode("utf8"))

            self.assertEqual("Ok", response.payload.decode("utf8"))

    @attr('system')
    def test_register_service_call_from_request_callback(self):
        # While in the request callback for a service invocation, attempt to
        # register a second service. Confirm that a call to the second service
        # is successful. This test ensures that concurrent add/remove service
        # calls and processing of incoming messages do not produce deadlocks.
        with self.create_client(self.DEFAULT_RETRIES, 2) as client:
            expected_second_service_response_payload =\
                "Second service request okay too"
            second_service_callback = RequestCallback()

            def on_second_service_request(request):
                response = Response(request)
                response.payload = expected_second_service_response_payload
                try:
                    client.send_response(response)
                except DxlException as ex:
                    print("Failed to send response" + str(ex))

            second_service_callback.on_request = on_second_service_request

            second_service_info = ServiceRegistrationInfo(
                client, "/mcafee/service/JTI2")
            second_service_info.add_topic(
                "/mcafee/service/JTI2/file/reputation/" +
                second_service_info.service_id, second_service_callback)

            def register_second_service():
                client.register_service_sync(second_service_info,
                                             self.REG_DELAY)

            register_second_service_thread = threading.Thread(
                target=register_second_service)
            register_second_service_thread.daemon = True

            # Perform the second service registration from a separate thread
            # in order to ensure that locks taken by the callback and
            # service managers do not produce deadlocks between the
            # thread from which the service registration request is made and
            # any threads on which response messages are received from the
            # broker.
            def on_first_service_request():
                register_second_service_thread.start()
                register_second_service_thread.join()

            self.add_client_callbacks(client, on_first_service_request)
            client.connect()
            client.register_service_sync(self.info, self.REG_DELAY)

            first_service_request = Request(
                "/mcafee/service/JTI/file/reputation/" + self.info.service_id)
            first_service_request.payload = "Test"

            first_service_response = client.sync_request(
                first_service_request, self.POST_OP_DELAY)
            first_service_response_payload = first_service_response.\
                payload.decode("utf8")
            logging.info("First service response payload: %s",
                first_service_response_payload)

            self.assertEqual("Ok",
                              first_service_response_payload)

            second_service_request = Request(
                "/mcafee/service/JTI2/file/reputation/" +
                second_service_info.service_id)
            second_service_request.payload = "Test"

            second_service_response = client.sync_request(
                second_service_request, self.POST_OP_DELAY)
            actual_second_service_response_payload = second_service_response. \
                payload.decode("utf8")
            logging.info("Second service response payload: %s",
                         actual_second_service_response_payload)

            self.assertEqual(expected_second_service_response_payload,
                             actual_second_service_response_payload)

    @attr('system')
    def test_register_service_weak_reference_before_connect(self):

        with self.create_client() as client:
            self.add_client_callbacks(client)

            client.register_service_async(self.info)

            service_id = self.info.service_id
            self.assertTrue(self.service_ref_valid(client, service_id))

            # Deleted the service registration
            self.info = 1

            # Enforce garbage collection
            gc.collect()

            # Weak reference should freed after a few seconds
            self.assertTrue(self.wait_for_service_reference_to_be_freed(
                client, service_id))

            client.connect()
            self.assertTrue(client.connected)

        self.assertEqual(0, self.info_registrations)
        self.assertEqual(0, self.info_unregistrations)

    @attr('system')
    def test_register_service_weak_reference_after_connect(self):

        with self.create_client() as client:
            self.add_client_callbacks(client)
            client.register_service_async(self.info)

            client.connect()

            self.assertTrue(self.wait_info_registered())

            # Deleted the service registration
            self.info = 1

            # Enforce garbage collection
            gc.collect()

            # Service should be implicitly unregistered from the broker
            # as the weak reference to the service is cleaned up.
            self.assertTrue(self.wait_info_not_registered())

        self.assertEqual(1, self.info_registrations)

    @attr('system')
    def test_register_service_weak_reference_after_connect_and_send_request(self):

        with self.create_client() as client:
            self.add_client_callbacks(client)

            client.register_service_async(self.info)
            client.connect()

            service_id = self.info.service_id
            self.assertTrue(self.wait_info_registered())

            # Deleted the service registration
            self.info = 1

            # Enforce garbage collection
            gc.collect()

            # Service should be implicitly unregistered from the broker
            # as the weak reference to the service is cleaned up.
            self.assertTrue(self.wait_info_not_registered())

            # Sending an request should result in a WaitTimeoutException since
            # the destroy() method of ServiceRegistrationInfo will unregister
            # the service
            request = Request("/mcafee/service/JTI/file/reputation/" + service_id)
            request.payload = "Test"

            try:
                response = client.sync_request(request, 2)
                # Depending upon the timing, the broker can respond with 404 or the request might timeout
                # self.assertIsInstance(response, ErrorResponse, "response is instance of ErrorResponse")
                self.assertTrue(isinstance(response, ErrorResponse), response.__class__)
            except WaitTimeoutException as ex:
                self.assertIn(request.message_id, str(ex))

        self.assertEqual(1, self.info_registrations)
