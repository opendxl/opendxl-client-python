from dxlclient import Request, UuidGenerator
from dxlclient.test.base_test import BaseClientTest
from nose.plugins.attrib import attr

@attr('system')
class SubsCountTest(BaseClientTest):

    def _create_request(self, topic):
        req = Request("/mcafee/service/dxl/broker/subs")
        req.payload = "{\"topic\":\"" + topic + "\"}"
        return req

    @attr('system')
    def test_subs_count(self):
        clients = []

        with self.create_client() as client:
            client.connect()

            for i in range(6):
                c = self.create_client()
                c.connect()
                clients.append(c)

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

            # Topic 1
            req = self._create_request(topic1)
            resp = client.sync_request(req, 5)
            pl = str(resp.payload)
            self.assertTrue(":6}" in pl)

            # Topic 2
            req = self._create_request(topic2)
            resp = client.sync_request(req, 5)
            pl = str(resp.payload)
            self.assertTrue(":3}" in pl)

            print "Test passed!"
