from threading import Condition
from base_test import BaseClientTest, atomize
from dxlclient import UuidGenerator, ServiceRegistrationInfo, Request, ErrorResponse
from dxlclient.test.test_service import TestService
from thread_executor import ThreadRunExecutor
import logging
import time
from nose.plugins.attrib import attr


class SyncRequestTroughputRunner(BaseClientTest):

    # The number of requests to send
    THREAD_COUNT = 100
    REQUEST_COUNT = 10

    # The maximum time for the test
    MAX_TIME = 10 * 60
    # The maximum time to wait between connections
    MAX_CONNECT_WAIT = 2 * 60
    # The number of times to try to connect to the broker
    MAX_CONNECT_RETRIES = 10

    connect_condition = Condition()
    response_count_condition = Condition()
    requests_start_time_condition = Condition()
    connect_time_condition = Condition()
    connect_retries_condition = Condition()
    cummulative_response_time_condition = Condition()

    _atomic_cummulative_response_time = 0
    _atomic_response_count = 0
    _atomic_connect_retries = 0
    _atomic_connect_count = 0
    _atomic_connect_time = 0
    _atomic_requests_start_time = 0

    requests_end_time = 0
    response_times = []

    @property
    @atomize(requests_start_time_condition)
    def requests_start_time(self):
        return self._atomic_requests_start_time

    @requests_start_time.setter
    @atomize(requests_start_time_condition)
    def requests_start_time(self, requests_start_time):
        self._atomic_requests_start_time = requests_start_time

    @property
    @atomize(connect_time_condition)
    def connect_time(self):
        return self._atomic_connect_time

    @connect_time.setter
    @atomize(connect_time_condition)
    def connect_time(self, connect_time):
        self._atomic_connect_time = connect_time

    @property
    def response_count(self):
        return self._atomic_response_count

    @response_count.setter
    def response_count(self, response_count):
        self._atomic_response_count = response_count

    @property
    @atomize(connect_retries_condition)
    def connect_retries(self):
        return self._atomic_connect_retries

    @connect_retries.setter
    @atomize(connect_retries_condition)
    def connect_retries(self, connect_retries):
        self._atomic_connect_retries = connect_retries

    @property
    @atomize(cummulative_response_time_condition)
    def cummulative_response_time(self):
        return self._atomic_cummulative_response_time

    @cummulative_response_time.setter
    @atomize(cummulative_response_time_condition)
    def cummulative_response_time(self, cummulative_response_time):
        self._atomic_cummulative_response_time = cummulative_response_time

    @property
    def atomic_connect_count(self):
        return self._atomic_connect_count

    @atomic_connect_count.setter
    def atomic_connect_count(self, connect_count):
        self._atomic_connect_count = connect_count

    @attr('load')
    def test_sync_request_troughput(self):
        self.execute_t(self.create_client)
        print self.get_execution_results()

    def get_execution_results(self):
        total_time = self.requests_end_time - self.requests_start_time
        output = "Connect time: " + str(self.connect_time) + "\n"
        output += "Connect retries: " + str(self.connect_retries) + "\n"
        output += "Request time: " + str(total_time) + "\n"
        output += "Total requests: " + str(self.THREAD_COUNT * self.REQUEST_COUNT) + "\n"
        output += "Requests/second: " + str((self.THREAD_COUNT * self.REQUEST_COUNT) / total_time) + "\n"
        output += "Average response time: " + str(self.cummulative_response_time /
                                                  (self.THREAD_COUNT * self.REQUEST_COUNT)) + "\n"

        mid = (self.THREAD_COUNT * self.REQUEST_COUNT) / 2
        self.response_times.sort()
        if (self.THREAD_COUNT * self.REQUEST_COUNT) % 2 == 0:
            median_response_time = self.response_times[mid] + self.response_times[mid-1] / 2
        else:
            median_response_time = self.response_times[mid]

        output += "Median response time: " + str(median_response_time)
        return output

    def execute_t(self, client_factory):

        with client_factory() as server_client:
            test_service = TestService(server_client, 1)
            connect_time_start = time.time()
            server_client.connect()
            topic = UuidGenerator.generate_id_as_string()
            reg_info = ServiceRegistrationInfo(server_client, "syncRequestThroughputRunnerService")
            reg_info.add_topic(topic, test_service)
            server_client.register_service_sync(reg_info, self.DEFAULT_TIMEOUT)

            #
            # Create a thread for each request. Wait for all of the clients to connect
            # to the broker before starting to calculate response related statistics.
            #

            executor = ThreadRunExecutor(self.THREAD_COUNT)

            def run():
                try:
                    with client_factory(max_retries=0) as client:
                        retries = self.MAX_CONNECT_RETRIES
                        connected = False
                        while not connected and retries > 0:
                            try:
                                client.connect()
                                connected = True
                            except Exception:
                                if retries > 0:
                                    retries -= 1
                                    self.connect_retries += 1
                        self.assertTrue(connected, "Unable to connect after retries")

                        # Waiting all clients have connected
                        with self.connect_condition:
                            self.atomic_connect_count += 1
                            self.connect_condition.notify_all()

                            while self.atomic_connect_count != self.THREAD_COUNT:
                                curr_count = self.atomic_connect_count
                                self.connect_condition.wait(self.MAX_CONNECT_WAIT)
                                if self.atomic_connect_count == curr_count:
                                    self.fail( "Timeout waiting for all threads to connect" )

                            # Once all clients have connected, reset timing information
                            if self.requests_start_time == 0:
                                self.requests_start_time = time.time()
                                self.connect_time = self.requests_start_time - connect_time_start

                        for i in range(0, self.REQUEST_COUNT):
                            req = Request(topic)
                            call_start_time = time.time()
                            response = client.sync_request(req, timeout=self.DEFAULT_TIMEOUT)
                            response_time = time.time() - call_start_time
                            self.assertNotIsInstance(response, ErrorResponse)

                            with self.response_count_condition:
                                self.response_count += 1
                                count = self.response_count
                                if (self.requests_end_time == 0) and \
                                        (count == (self.THREAD_COUNT * self.REQUEST_COUNT)):
                                    self.requests_end_time = time.time()

                            if count % 100 is 0:
                                print str(count) + ", " + str(time.time() - self.requests_start_time)

                            # Calulate and track response times
                            self.cummulative_response_time = self.cummulative_response_time + response_time
                            self.response_times.append(response_time)

                except Exception, e:
                    print e
                    logging.info(e.message)
                    raise e
            executor.execute(run)

            if self.THREAD_COUNT != self.response_count / self.REQUEST_COUNT:
                print "Failed! responseCount=" + str(self.response_count)
            self.assertEqual(self.THREAD_COUNT, self.response_count / self.REQUEST_COUNT)

            server_client.unregister_service_sync(reg_info, self.DEFAULT_TIMEOUT)
