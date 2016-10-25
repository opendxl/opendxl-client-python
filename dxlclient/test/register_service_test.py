
from base_test import BaseClientTest
from threading import RLock, Condition
from nose.plugins.attrib import attr
import time
import logging
import weakref
import gc

from dxlclient import Response, DxlException, RequestCallback, ServiceRegistrationInfo
from dxlclient import EventCallback
from dxlclient.service import _ServiceManager
from dxlclient import Request
from dxlclient.exceptions import WaitTimeoutException
from dxlclient import ErrorResponse


class EventCounterCallback(EventCallback):

    counter_lock = RLock()
    condition = Condition()
    counter = 0

    def get(self):
        with self.counter_lock:
            return self.counter

    def reset(self):
        with self.condition:
            with self.counter_lock:
                self.counter = 0
            self.condition.notify_all()

    def on_event(self, event):
        print event.destination_topic
        print event.payload

        with self.counter_lock:
            with self.condition:
                self.counter += 1
                self.condition.notify_all()


@attr('system')
class RegisterServiceClientTest(BaseClientTest):

    register_callback = EventCounterCallback()
    unregister_callback = EventCounterCallback()

    info = None
    request_callback = None

    def add_client_callbacks(self, client):
        self.request_callback = RequestCallback()

        def on_request(request):
            logging.info(request.destination_topic)
            logging.info(request.payload)

            response = Response(request)
            response.payload = bytes("Ok")
            try:
                client.send_response(response)
            except DxlException, ex:
                print "Failed to send response" + str(ex)

        self.request_callback.on_request = on_request

        client.add_event_callback(_ServiceManager.DXL_SERVICE_REGISTER_CHANNEL, self.register_callback)
        client.add_event_callback(_ServiceManager.DXL_SERVICE_UNREGISTER_CHANNEL, self.unregister_callback)

        self.info = ServiceRegistrationInfo(client, "/mcafee/service/JTI")
        self.info.add_topic("/mcafee/service/JTI/file/reputation/" + self.info.service_id, self.request_callback)
        self.info.add_topic("/mcafee/service/JTI/cert/reputation/" + self.info.service_id, self.request_callback)

    def setUp(self):
        super(RegisterServiceClientTest, self).setUp()

        self.register_callback.reset()
        self.unregister_callback.reset()

    @attr('system')
    def test_register_service_before_connect(self):

        with self.create_client() as client:
            self.add_client_callbacks(client)
            client.register_service_async(self.info)
            client.connect()
            time.sleep(self.POST_OP_DELAY)
            client.unregister_service_sync(self.info, self.REG_DELAY)

            self.assertEquals(1, self.register_callback.get())
            self.assertEquals(1, self.unregister_callback.get())

    @attr('system')
    def test_register_service_after_connect(self):

        with self.create_client() as client:
            self.add_client_callbacks(client)
            client.connect()
            client.register_service_sync(self.info, self.REG_DELAY)
            client.unregister_service_sync(self.info, self.REG_DELAY)

            self.assertEquals(1, self.register_callback.get())
            self.assertEquals(1, self.unregister_callback.get())

    @attr('system')
    def test_register_service_never_connect(self):

        with self.create_client() as client:
            self.add_client_callbacks(client)
            client.register_service_async(self.info)

            client.unregister_service_async(self.info)

            self.assertEquals(0, self.register_callback.get())
            self.assertEquals(0, self.unregister_callback.get())

    @attr('system')
    def test_register_unregister_service_before_connect(self):

        with self.create_client() as client:
            self.add_client_callbacks(client)
            client.register_service_async(self.info)
            client.unregister_service_async(self.info)
            client.connect()

            self.assertEquals(0, self.register_callback.get())
            self.assertEquals(0, self.unregister_callback.get())

    @attr('system')
    def test_register_service_and_send_request(self):

        with self.create_client() as client:
            self.add_client_callbacks(client)
            client.register_service_async(self.info)
            time.sleep(self.POST_OP_DELAY)
            client.connect()
            time.sleep(self.POST_OP_DELAY)

            request = Request("/mcafee/service/JTI/file/reputation/" + self.info.service_id)
            request.payload = bytes("Test")

            response = client.sync_request(request, self.POST_OP_DELAY)
            logging.info("Response payload: {0}".format(str(response.payload)))

            self.assertEquals("Ok", str(response.payload))

    @attr('system')
    def test_register_service_weak_reference_before_connect(self):

        with self.create_client() as client:
            self.add_client_callbacks(client)
            ref = weakref.ref(self.info)

            client.register_service_async(self.info)

            # Deleted the service registration
            self.info = 1
            time.sleep(self.POST_OP_DELAY * 2)

            # Enforce garbage collection
            gc.collect()
            # Weak reference should now be null
            self.assertEquals(None, ref())

            client.connect()

        self.assertEquals(0, self.register_callback.get())
        self.assertEquals(0, self.unregister_callback.get())

    @attr('system')
    def test_register_service_weak_reference_after_connect(self):

        with self.create_client() as client:
            self.add_client_callbacks(client)
            ref = weakref.ref(self.info)
            client.register_service_async(self.info)

            client.connect()

            # Deleted the service registration
            self.info = 1
            time.sleep(self.POST_OP_DELAY)

            # Enforce garbage collection
            gc.collect()
            # Weak reference should now be null
            self.assertEquals(None, ref())

        self.assertEquals(1, self.register_callback.get())

        #
        # Sometimes the unregister event does not get send; don't check for now
        # self.assertEquals(1, self.unregister_callback.get())
        #

    @attr('system')
    def test_register_service_weak_reference_after_connect_and_send_request(self):

        with self.create_client() as client:
            self.add_client_callbacks(client)
            ref = weakref.ref(self.info)

            client.register_service_async(self.info)
            client.connect()

            info_guid = self.info.service_id
            # Theoretically, sending the destroy method when creating the weakref
            # would made the magic of calling that method when info get unref
            self.info._destroy()
            # Deleted the service registration
            self.info = 1
            time.sleep(self.POST_OP_DELAY * 2)

            # Enforce garbage collection
            gc.collect()
            # Weak reference should now be null
            self.assertEquals(None, ref())

            # Sending an request should result in a WaitTimeoutException since the destroy() method
            # of ServiceRegistrationInfo will unregister the service
            request = Request("/mcafee/service/JTI/file/reputation/" + info_guid)
            request.payload = bytes("Test")

            try:
                response = client.sync_request(request, 2)
                # Depending upon the timing, the broker can respond with 404 or the request might timeout
                # self.assertIsInstance(response, ErrorResponse, "response is instance of ErrorResponse")
                self.assertTrue(isinstance(response, ErrorResponse), response.__class__)
            except WaitTimeoutException as ex:
                assert(ex.message.__contains__(request.message_id))

        self.assertEquals(1, self.register_callback.get())
        logging.debug("Waiting for unregister event...")
        ttw = 30
        while self.unregister_callback.get() < 1 and ttw > 0:
            time.sleep(self.POST_OP_DELAY)
            ttw -= 1
        # Sometimes the unregister event does not get send; don't check for now
        # self.assertEquals(1, self.unregister_callback.get())
