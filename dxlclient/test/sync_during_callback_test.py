from __future__ import absolute_import
from threading import Condition
import time
from dxlclient import UuidGenerator, Request, EventCallback, Event
from dxlclient.test.base_test import BaseClientTest
from nose.plugins.attrib import attr
import sys

@attr('system')
class TestSyncDuringCallback(BaseClientTest):

    MAX_WAIT = 60
    request_exception_message = None
    event_received = False
    event_received_condition = Condition()

    # Test to ensure that synchronous requests can't be made on
    # the incoming message thread
    def test_execute_sync_during_callback(self):

        event_topic = UuidGenerator.generate_id_as_string()
        req_topic = UuidGenerator.generate_id_as_string()

        with self.create_client() as client:
            client.connect()

            # callback
            def event_callback(event):
                with self.event_received_condition:
                    self.event_received = True
                    try:
                        req = Request(destination_topic=req_topic)
                        client.sync_request(req)
                    except Exception as e:
                        self.request_exception_message = str(e)
                    self.event_received_condition.notify_all()

            ec = EventCallback()
            ec.on_event = event_callback

            client.add_event_callback(event_topic, ec)

            evt = Event(destination_topic=event_topic)
            client.send_event(evt)

            start = time.time()
            with self.event_received_condition:
                while (time.time() - start < self.MAX_WAIT) and \
                        not self.event_received:
                    self.event_received_condition.wait(self.MAX_WAIT)
            self.assertIsNotNone(self.request_exception_message)
            self.assertIn("different thread", self.request_exception_message)
