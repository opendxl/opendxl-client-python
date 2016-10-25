import time
from dxlclient import ServiceRegistrationInfo, UuidGenerator
from dxlclient import RequestCallback, Response, Message, ResponseCallback, Request
from dxlclient.test.base_test import BaseClientTest
from threading import Condition
from nose.plugins.attrib import attr


#
# Slams a service with a flood of asynchronous tests. The PAHO library by default will
# deadlock when it is waiting to complete a publish and at the same time receives an
# incoming message.
#
# This test ensures that the changes we made to the PAHO library now work in this particular
# scenario.
#
@attr('system')
class AsyncFloodTest(BaseClientTest):
    # The count of requests to send
    REQUEST_COUNT = 1000

    # Amount of time to wait for the test to succeed
    WAIT_TIME = 90

    # The service registration information
    m_info = None

    resp_condition = Condition()
    response_count = 0
    error_count = 0

    @attr('system')
    def test_async_flood(self):

        channel = UuidGenerator.generate_id_as_string()

        with self.create_client() as client:

            self.m_info = ServiceRegistrationInfo(client, channel)
            client.connect()
            client.subscribe(channel)

            def my_request_callback(rq):
                # print "request: " + str(rq.version)
                try:
                    time.sleep(0.05)
                    resp = Response(rq)
                    resp.payload = rq.payload
                    client.send_response(resp)
                except Exception, e:
                    print e.message

            req_callback = RequestCallback()
            req_callback.on_request = my_request_callback

            self.m_info.add_topic(channel, req_callback)
            client.register_service_sync(self.m_info, 10)

            with self.create_client() as client2:
                client2.connect()

                def my_response_callback(response):
                    # print "response"
                    if response.message_type == Message.MESSAGE_TYPE_ERROR:
                        print "Received error response: " + response._error_response
                        with self.resp_condition:
                            self.error_count += 1
                            self.resp_condition.notify_all()
                    else:
                        with self.resp_condition:
                            if self.response_count % 10 == 0:
                                print "Received request " + str(self.response_count)
                            self.response_count += 1
                            self.resp_condition.notify_all()

                callback = ResponseCallback()
                callback.on_response = my_response_callback

                client2.add_response_callback("", callback)

                for i in range(0, self.REQUEST_COUNT):
                    if i % 100 == 0:
                        print "Sent: " + str(i)

                    request = Request(channel)
                    pl = str(i)
                    request.payload = pl
                    client2.async_request(request)

                    if self.error_count > 0:
                        break

                # Wait for all responses, an error to occur, or we timeout
                start_time = time.time()
                with self.resp_condition:
                    while (self.response_count != self.REQUEST_COUNT) and (self.error_count == 0) and (time.time() - start_time < self.WAIT_TIME):
                        self.resp_condition.wait(5)

                if self.error_count != 0:
                    exc = Exception()
                    exc.message = "Received an error response!"
                    raise exc

                self.assertEquals(self.REQUEST_COUNT, self.response_count, "Did not receive all messages!")
