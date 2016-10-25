from threading import Condition
from dxlclient.test.base_test import BaseClientTest
from dxlclient.test.test_service import TestService
from nose.plugins.attrib import attr
from dxlclient import ServiceRegistrationInfo, Request, ErrorResponse
from thread_executor import ThreadRunExecutor

@attr('system')
class SyncRequestTests(BaseClientTest):

    # The number of requests to send
    REQUEST_COUNT = 500
    # Maximum time to wait for the test to complete
    MAX_WAIT = 5 * 60
    # Maximum time to wait for a response
    RESPONSE_WAIT = 60

    response_count = 0
    response_count_condition = Condition()

    event_condition = Condition()

    #
    # Tests the synchronous request methods of the DxlClient.
    #
    @attr('system')
    def test_execute_sync_request(self):
        with self.create_client(max_retries=0) as client:
            # Create a test service that responds to requests on a particular topic.
            test_service = TestService(client, 1)
            client.connect()
            topic = "event_testing"  # UuidGenerator.generate_id_as_string()
            reg_info = ServiceRegistrationInfo(client, "sync_request_runner_service")
            reg_info.add_topic(topic, test_service)
            # Register the service
            client.register_service_sync(reg_info, self.DEFAULT_TIMEOUT)

            executor = ThreadRunExecutor(self.REQUEST_COUNT)

            # Sends synchronous requests with a unique thread for each request. Ensure that the
            # response that is received corresponds with the request that was sent. Also, keep
            # track of the total number of responses received.
            def run():
                try:
                    request = Request(topic)
                    response = client.sync_request(request, timeout=self.RESPONSE_WAIT)
                    self.assertNotIsInstance(response, ErrorResponse)
                    self.assertEquals(request.message_id, response.request_message_id)

                    with self.response_count_condition:
                        self.response_count += 1
                        if self.response_count % 100 == 0:
                            print self.response_count
                        self.response_count_condition.notify_all()
                except Exception, e:
                    print e.message
                    raise e

            executor.execute(run)

            # Wait for all of the requests to complete
            with self.response_count_condition:
                while self.response_count != self.REQUEST_COUNT:
                    current_count = self.response_count
                    self.response_count_condition.wait(self.MAX_WAIT)
                    if current_count == self.response_count:
                        self.fail("Request wait timeout.")

            self.assertEquals(self.REQUEST_COUNT, self.response_count)
