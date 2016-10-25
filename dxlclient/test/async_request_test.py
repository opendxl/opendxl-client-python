from threading import Condition
from dxlclient.test.test_service import TestService
from dxlclient import UuidGenerator, Request, ResponseCallback, ServiceRegistrationInfo
from dxlclient.test.base_test import BaseClientTest, atomize
from nose.plugins.attrib import attr


class AsyncRequestTests(BaseClientTest):

    # The number of requests to send
    REQ_COUNT = 100
    MAX_RESPONSE_WAIT = 1 * 60

    response_count = 0
    outstanding_requests = []
    # Conditions
    response_condition = Condition()
    outstanding_requests_condition = Condition()

    @atomize(outstanding_requests_condition)
    def append_outstanding_request(self, message_id):
        self.outstanding_requests.append(message_id)

    @atomize(outstanding_requests_condition)
    def remove_outstanding_request(self, message_id):
        self.outstanding_requests.remove(message_id)

    #
    # Tests the asynchronous request methods of the DxlClient.
    #
    @attr('system')
    def test_execute_async_request(self):

        # Create and register a response callback. Once the request has been processed
        # by the service, the requesting client will receive a notification via this
        # callback. At that point, we note that the request has been responded to (remove
        # it from the set of outstanding requests), and increment the count of responses
        # we have received via the callbacks.
        def my_response(response):
            with self.response_condition:
                # Increment count of responses received
                self.response_count += 1
                # Remove from outstanding requests
                self.remove_outstanding_request(response.request_message_id)
                # Notify that a response has been received (are we done yet?)
                self.response_condition.notify_all()
        rc = ResponseCallback()
        rc.on_response = my_response

        with self.create_client(max_retries=0) as client:
            try:
                client.connect()
                # Create a test service that responds to requests on a particular topic.
                test_service = TestService(client, 1)
                topic = UuidGenerator.generate_id_as_string()
                reg_info = ServiceRegistrationInfo(client, "async_request_runner_service")
                reg_info.add_topic(topic, test_service)
                # Register the service
                client.register_service_sync(reg_info, self.DEFAULT_TIMEOUT)
                # Add a response callback (not channel-specific)
                client.add_response_callback("", rc)

                for i in range(0, self.REQ_COUNT):
                    # Send a request without specifying a callback for the current request
                    req = Request(topic)
                    self.append_outstanding_request(req.message_id)
                    client.async_request(req)

                    # Send a request with a specific callback that is to receive the response.
                    # The response will be received by two callbacks.
                    req = Request(topic)
                    self.append_outstanding_request(req.message_id)
                    client.async_request(req, response_callback=rc)

                # Wait until all the responses are received via the response callbacks.
                # The "times 3" is due to the fact that 20000 requests were sent in total.
                # 20000 were handled via the global callback, an additional 10000 were handled
                # via the callback explicitly passed in the second set of requests.
                with self.response_condition:
                    while self.response_count != self.REQ_COUNT * 3:
                        current_count = self.response_count
                        self.response_condition.wait(self.MAX_RESPONSE_WAIT)
                        if current_count == self.response_count:
                            self.fail("Response wait timeout")

                # Make sure there are no outstanding requests
                self.assertEqual(0, len(self.outstanding_requests))
                print "Async request test: PASSED"

            except Exception, ex:
                print ex.message
                raise ex
