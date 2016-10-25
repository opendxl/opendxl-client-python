import time
from dxlclient import UuidGenerator, Request, EventCallback, Event
from dxlclient.test.base_test import BaseClientTest
from nose.plugins.attrib import attr

@attr('system')
class TestSyncDuringCallback(BaseClientTest):

    SLEEP_TIME = 5
    exceptions = []

    # Test to ensure that synchronous requests can't be made on
    # the incoming message thread
    def test_execute_sync_during_callback(self):

        event_topic = UuidGenerator.generate_id_as_string()
        req_topic = UuidGenerator.generate_id_as_string()

        with self.create_client() as client:
            client.connect()

            # callback
            def event_callback(event):
                try:
                    req = Request(destination_topic=req_topic)
                    client.sync_request(req)
                except Exception, e:
                    self.exceptions.append(e)
                    raise e

            ec = EventCallback()
            ec.on_event = event_callback

            client.add_event_callback(event_topic, ec)

            time.sleep(self.SLEEP_TIME)  # Check the time

            evt = Event(destination_topic=event_topic)
            client.send_event(evt)

            time.sleep(self.SLEEP_TIME)

            self.assertTrue(self.exceptions[0] is not None)
            self.assertTrue("different thread" in self.exceptions[0].message)
