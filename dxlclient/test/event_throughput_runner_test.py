import logging
import time
from threading import Condition

from dxlclient import EventCallback, Event, UuidGenerator
from dxlclient.test.base_test import BaseClientTest, atomize
from dxlclient.test.thread_executor import ThreadRunExecutor
from nose.plugins.attrib import attr


class EventThroughputRunner(BaseClientTest):
    # The number of events to send
    THREAD_COUNT = 100
    EVENT_COUNT = 100

    # The maximum time for the test
    MAX_TIME = 10 * 60
    # The maximum time to wait between connections
    MAX_CONNECT_WAIT = 2 * 60
    # The number of times to try to connect to the broker
    MAX_CONNECT_RETRIES = 10

    connect_condition = Condition()
    connect_count_condition = Condition()
    event_count_condition = Condition()
    connect_time_condition = Condition()
    requests_start_time_condition = Condition()
    connect_retries_condition = Condition()

    _atomic_event_count = 0
    _atomic_connect_retries = 0
    _atomic_connect_count = 0
    _atomic_connect_time = 0
    _atomic_requests_start_time = 0

    connect_time_start = 0
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
    def event_count(self):
        return self._atomic_event_count

    @event_count.setter
    def event_count(self, event_count):
        self._atomic_event_count = event_count

    @property
    @atomize(connect_retries_condition)
    def connect_retries(self):
        return self._atomic_connect_retries

    @connect_retries.setter
    @atomize(connect_retries_condition)
    def connect_retries(self, connect_retries):
        self._atomic_connect_retries = connect_retries

    @property
    def atomic_connect_count(self):
        return self._atomic_connect_count

    @atomic_connect_count.setter
    def atomic_connect_count(self, connect_count):
        self._atomic_connect_count = connect_count

    @attr('event_test')
    def test_event_troughput(self):
        self.execute_t(self.create_client)
        # print self.get_statistics()

    def execute_t(self, client_factory):
        self.threads = 0
        with client_factory() as send_client:
            send_client.connect()
            event_topic = UuidGenerator.generate_id_as_string()
            executor = ThreadRunExecutor(self.THREAD_COUNT)

            def run():
                try:
                    with client_factory(max_retries=0) as client:
                        retries = self.MAX_CONNECT_RETRIES
                        connected = False
                        while not connected and retries > 0:
                            try:
                                self.connect_time_start = time.time()
                                client.connect()
                                connected = True
                            except Exception:
                                if retries > 0:
                                    retries -= 1
                                    self.connect_retries += 1

                        self.assertTrue(connected, "Unable to connect after retries")

                        def on_event(event):
                            with self.event_count_condition:
                                self.event_count += 1
                                current_count = self.event_count
                                self.event_count_condition.notify_all()

                                if current_count % 100 == 0:
                                    print client.config._client_id + " : " + str(current_count) + " : " + event.payload

                        # callback registration
                        callback = EventCallback()
                        callback.on_event = on_event
                        client.add_event_callback(event_topic, callback)

                        # Waiting all clients have connected
                        with self.connect_condition:
                            self.atomic_connect_count += 1
                            curr_count = self.atomic_connect_count

                            self.connect_condition.notify_all()
                            while self.atomic_connect_count != self.THREAD_COUNT:
                                self.connect_condition.wait(timeout=self.MAX_CONNECT_WAIT)
                                if curr_count == self.atomic_connect_count:
                                    self.fail("Timeout waiting for all threads to connect")

                            # Once all clients have connected, reset timing information
                            if self.requests_start_time == 0:
                                self.requests_start_time = time.time()
                                self.connect_time = self.requests_start_time - self.connect_time_start

                                for i in range(0, self.EVENT_COUNT):
                                    event = Event(event_topic)
                                    if i % 10 == 0:
                                        print "###send: " + str(i)
                                    event.payload = str(i)
                                    send_client.send_event(event)

                        with self.event_count_condition:
                            while self.event_count != self.EVENT_COUNT * self.THREAD_COUNT:
                                curr_count = self.event_count
                                self.event_count_condition.wait(timeout = self.MAX_CONNECT_WAIT)
                                if self.event_count == curr_count:
                                    self.fail("Timed out while receiving events")
                            self.event_count_condition.notify_all()
                            if self.requests_end_time == 0:
                                self.requests_end_time = time.time()

                except Exception, e:
                    logging.error(e.message)
                    raise e

            executor.execute(run)

            self.assertEquals(self.EVENT_COUNT * self.THREAD_COUNT, self.event_count)

            total_time = self.requests_end_time - self.requests_start_time
            print "Connect time: " + str(self.connect_time)
            print "Connect retries: " + str(self.connect_retries)
            print "Total events: " + str(self.EVENT_COUNT)
            print "Events/second: " + str(self.EVENT_COUNT / total_time)
            print "Total events received: " + str(self.EVENT_COUNT * self.THREAD_COUNT)
            print "Total events received/second: " + str((self.EVENT_COUNT * self.THREAD_COUNT) / total_time)
            print "Elapsed time: " + str(total_time)
