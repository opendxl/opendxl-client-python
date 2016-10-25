from threading import Condition
from dxlclient import UuidGenerator, EventCallback, Event
from dxlclient.test.base_test import BaseClientTest, atomize
from nose.plugins.attrib import attr

@attr('system')
class EventTests(BaseClientTest):

    # The number of events to send
    EVENT_COUNT = 10000
    MAX_EVENT_WAIT = 2 * 60

    event_count = 0
    outstanding_events = []
    # Conditions
    event_condition = Condition()
    outstanding_events_condition = Condition()

    @atomize(outstanding_events_condition)
    def append_outstanding_event(self, message_id):
        self.outstanding_events.append(message_id)

    @atomize(outstanding_events_condition)
    def remove_outstanding_event(self, message_id):
        self.outstanding_events.remove(message_id)

    #
    # Tests the events-related methods of the DxlClient.
    #
    @attr('system')
    def test_execute_events(self):
        with self.create_client(max_retries=0) as client:
            try:
                client.connect()

                topic = UuidGenerator.generate_id_as_string()

                # Create and register an event callback. Ensure that all sent events are received
                # (via the outstanding events set). Also, track the number of total events received.
                def event_callback(event):
                    with self.event_condition:
                        # Increment count of responses received
                        self.event_count += 1
                        # Remove from outstanding events
                        self.remove_outstanding_event(event.message_id)
                        # Notify that a response has been received (are we done yet?)
                        self.event_condition.notify_all()

                ec = EventCallback()
                ec.on_event = event_callback

                client.add_event_callback(topic, ec)

                for i in range(0, self.EVENT_COUNT):
                    e = Event(topic)
                    self.append_outstanding_event(e.message_id)
                    client.send_event(e)

                with self.event_condition:
                    while self.event_count != self.EVENT_COUNT:                    
                        current_count = self.event_count
                        self.event_condition.wait(self.MAX_EVENT_WAIT)
                        if current_count == self.event_count:
                            self.fail("Event wait timeout.")

                self.assertEqual(0, len(self.outstanding_events))
                print "Events test: PASSED"

            except Exception, ex:
                print ex.message
                raise ex
