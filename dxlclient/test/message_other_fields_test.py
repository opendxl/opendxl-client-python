"""
Tests whether the 'other fields' dictionary in a message can be successfully
delivered from a client to the server.
"""

from __future__ import absolute_import
from __future__ import print_function
import time
from threading import Condition

from nose.plugins.attrib import attr

from dxlclient import UuidGenerator, Event, EventCallback
from dxlclient.test.base_test import BaseClientTest

# pylint: disable=missing-docstring


@attr('system')
class MessageOtherFieldsTest(BaseClientTest):

    MAX_WAIT = 1 * 60
    OTHER_FIELDS_COUNT = 1000

    event_received = None
    event_received_condition = Condition()

    @attr('system')
    def test_execute_message_other_fields(self):
        with self.create_client(max_retries=0) as client:
            client.connect()
            topic = UuidGenerator.generate_id_as_string()
            def on_event(event):
                with self.event_received_condition:
                    try:
                        self.event_received = event
                    except Exception as ex: # pylint: disable=broad-except
                        print(ex)
                    self.event_received_condition.notify_all()

            event_callback = EventCallback()
            event_callback.on_event = on_event
            client.add_event_callback(topic, event_callback)

            event = Event(destination_topic=topic)
            event.other_fields = {"key" + str(i): "value" + str(i)
                                  for i in range(self.OTHER_FIELDS_COUNT)}
            event.other_fields[b"key_as_bytes"] = b"val_as_bytes"
            client.send_event(event)
            # Bytes values for other field keys/values are expected to be
            # converted to unicode strings as received from the DXL fabric.
            del event.other_fields[b"key_as_bytes"]
            event.other_fields[u"key_as_bytes"] = u"val_as_bytes"
            start = time.time()
            with self.event_received_condition:
                while (time.time() - start < self.MAX_WAIT) and \
                        not self.event_received:
                    self.event_received_condition.wait(self.MAX_WAIT)

            self.assertIsNotNone(self.event_received)
            self.assertEqual(event.other_fields,
                             self.event_received.other_fields)
