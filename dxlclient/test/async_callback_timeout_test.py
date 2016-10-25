import time
from nose.plugins.attrib import attr
from dxlclient import ResponseCallback, UuidGenerator, ServiceRegistrationInfo, Request
from dxlclient.test.base_test import BaseClientTest
from dxlclient.test.test_service import TestService


class AsyncCallbackTimeoutTest(BaseClientTest):

    @attr('manual')
    def test_execute_async_callback_timeout(self):

        # TODO: Set SYSPROP_ASYNC_CALLBACK_CHECK_INTERVAL = 10000 when it is available
        def resp_callback():
            pass

        cb = ResponseCallback()
        cb.on_response = resp_callback

        with self.create_client() as client:
            client.connect()

            req_topic = UuidGenerator.generate_id_as_string()
            missing_topic = UuidGenerator.generate_id_as_string()

            test_service = TestService(client, 1)

            def empty_on_request(request):
                pass

            test_service.on_request = empty_on_request

            reg_info = ServiceRegistrationInfo(client, "async_callback_test_service")
            reg_info.add_topic(req_topic, test_service)
            # Register the service
            client.register_service_sync(reg_info, self.DEFAULT_TIMEOUT)

            async_req = Request(destination_topic=req_topic)
            client.async_request(async_req, cb)  # TODO: Use the method with timeout when is will available

            for i in range(0, 10):
                req = Request(destination_topic=req_topic)
                client.async_request(req, cb)  # TODO: Use the updated method with timeout when it is available

            req_for_error = Request(destination_topic=missing_topic)
            client.async_request(req_for_error)
            async_callback_count = client._get_async_callback_count()
            self.assertEquals(11, async_callback_count)

            for i in range(0, 20):
                print "asyncCallbackCount = " + str(client._get_async_callback_count())
                time.sleep(1)
                req = Request(destination_topic=req_topic)
                client.async_request(req, cb)

            self.assertEquals(1, async_callback_count)

        # TODO: Restore the value of SYSPROP_ASYNC_CALLBACK_CHECK_INTERVAL
