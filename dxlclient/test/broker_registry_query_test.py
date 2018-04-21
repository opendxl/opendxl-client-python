""" Tests the broker registry query. """

from __future__ import absolute_import
from __future__ import print_function
from nose.plugins.attrib import attr
from dxlclient.test.base_test import BaseClientTest
from dxlclient import Request, ErrorResponse

# pylint: disable=missing-docstring

@attr('system')
class BrokerRegistryQueryTest(BaseClientTest):

    @attr('system')
    def test_execute_registry_query(self):
        with self.create_client() as client:
            client.connect()
            topic = "/mcafee/service/dxl/brokerregistry/query"

            req = Request(topic)
            req.payload = "{}"
            response = client.sync_request(req)

            self.assertNotIsInstance(response, ErrorResponse)
            print("## sourceBrokerGuid: " + str(response.source_broker_id))
            print("## sourceClientGuid: " + str(response.source_client_id))
            print(str(response.payload))
