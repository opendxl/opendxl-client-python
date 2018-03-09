"""
Tests the broker/subs topic on the broker in conjunction with service
registrations made from the client.
"""

from __future__ import absolute_import
from __future__ import print_function
import json
import time
from nose.plugins.attrib import attr
from dxlclient import Request, UuidGenerator
from dxlclient.test.base_test import BaseClientTest

# pylint: disable=missing-docstring


@attr('system')
class SubsCountTest(BaseClientTest):
    MAX_TIME = 60

    @attr('system')
    def test_subs_count(self):
        clients = []

        with self.create_client() as client:
            client.connect()

            for _ in range(6):
                _client = self.create_client()
                _client.connect()
                clients.append(_client)

            random1 = UuidGenerator.generate_id_as_string()
            random2 = UuidGenerator.generate_id_as_string()
            topic1 = "/foo/bar/" + random1 + "/" + random2
            clients[0].subscribe(topic1)
            clients[1].subscribe(topic1)
            clients[2].subscribe(topic1)
            clients[3].subscribe("/foo/bar/" + random1 + "/#")
            clients[4].subscribe("/foo/+/" + random1 + "/#")

            topic2 = "/foo/baz/" + random2
            clients[1].subscribe(topic2)
            clients[2].subscribe(topic2)
            clients[5].subscribe("#")

            def get_subs_count(topic):
                req = Request("/mcafee/service/dxl/broker/subs")
                req.payload = "{\"topic\":\"" + topic + "\"}"
                resp = client.sync_request(req, 5)
                return json.loads(resp.payload.decode(
                    "utf8").rstrip("\0"))["count"]

            def loop_until_expected_subs_count(expected_topic_count, topic):
                topic_count = get_subs_count(topic)
                start = time.time()
                while topic_count != expected_topic_count and \
                        time.time() - start < self.MAX_TIME:
                    time.sleep(0.1)
                    topic_count = get_subs_count(topic)
                return topic_count

            # Topic 1
            expected_topic1_count = 6
            self.assertEqual(
                expected_topic1_count,
                loop_until_expected_subs_count(expected_topic1_count, topic1))

            # Topic 2
            expected_topic2_count = 3
            self.assertEqual(
                expected_topic2_count,
                loop_until_expected_subs_count(expected_topic2_count, topic2))

            for _client in clients:
                _client.destroy()
