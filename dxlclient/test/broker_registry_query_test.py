from dxlclient.test.base_test import BaseClientTest
from dxlclient import Request, ErrorResponse
from nose.plugins.attrib import attr

@attr('system')
class BrokerRegistryQueryTest(BaseClientTest):

    #
    # Tests Test the broker registry query.
    #
    @attr('system')
    def test_execute_registry_query(self):
        with self.create_client() as client:
            client.connect()
            topic = "/mcafee/service/dxl/brokerregistry/query"

            req = Request(topic)
            req.payload = "{}"
            response = client.sync_request(req)

            self.assertNotIsInstance(response, ErrorResponse)
            print "## sourceBrokerGuid: " + str(response.source_broker_id)
            print "## sourceClientGuid: " + str(response.source_client_id)
            print str(response.payload)
