# This sample queries McAfee Active Response for the IP addresses of hosts
# that have an Active Response client installed.

import os
import sys
import json
import time

from dxlclient.client import DxlClient
from dxlclient.client_config import DxlClientConfig
from dxlclient.message import Message, Request

# Import common logging and configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from common import *

# Configure local logger
logging.getLogger().setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# The topic to create a search
CREATE_SEARCH_TOPIC = "/mcafee/mar/service/api/search"

# Create DXL configuration from file
config = DxlClientConfig.create_dxl_config_from_file(CONFIG_FILE)


def execute_mar_search_api(client, payload_dict):
    """
    Executes a query against the MAR search api

    :param client: The DXL client
    :param payload_dict: The payload
    :return: A dictionary containing the results of the query
    """
    # Create the request message
    req = Request(CREATE_SEARCH_TOPIC)
    # Set the payload
    req.payload = json.dumps(payload_dict).encode(encoding="UTF-8")

    # Display the request that is going to be sent
    print "Request:\n" + json.dumps(payload_dict, sort_keys=True, indent=4, separators=(',', ': '))

    # Send the request and wait for a response (synchronous)
    res = client.sync_request(req, timeout=30)

    # Return a dictionary corresponding to the response payload
    if res.message_type != Message.MESSAGE_TYPE_ERROR:
        resp_dict = json.loads(res.payload.decode(encoding="UTF-8"))
        # Display the response
        print "Response:\n" + json.dumps(resp_dict, sort_keys=True, indent=4, separators=(',', ': '))
        if "code" in resp_dict:
            code = resp_dict['code']
            if code < 200 or code >= 300:
                if "body" in resp_dict and "applicationErrorList" in resp_dict["body"]:
                    error = resp_dict["body"]["applicationErrorList"][0]
                    raise Exception(error["message"] + ": " + str(error["code"]))
                elif "body" in resp_dict:
                    raise Exception(resp_dict["body"] + ": " + str(code))
                else:
                    raise Exception("Error: Received failure response code: " + str(code))
        else:
            raise Exception("Error: unable to find response code")
        return resp_dict
    else:
        raise Exception("Error: " + res.error_message + " (" + str(res.error_code) + ")")

# Create the client
with DxlClient(config) as client:

    # Connect to the fabric
    client.connect()

    # Create the search
    response_dict = execute_mar_search_api(client,
        {
            "target": "/v1/simple",
            "method": "POST",
            "parameters": {},
            "body": {
                "aggregated": True,
                "projections": [
                    {
                        "name": "HostInfo",
                        "outputs": ["ip_address"]
                    }
                ]
            }
        }
    )

    # Get the search identifier
    search_id = response_dict["body"]["id"]

    # Start the search
    execute_mar_search_api(client,
        {
            "target": "/v1/" + search_id + "/start",
            "method": "PUT",
            "parameters": {},
            "body": {}
        }
    )

    # Wait until the search finishes
    finished = False
    while not finished:
        response_dict = execute_mar_search_api(client,
            {
                "target": "/v1/" + search_id + "/status",
                "method": "GET",
                "parameters": {},
                "body": {}
            }
        )
        finished = response_dict["body"]["status"] == "FINISHED"
        if not finished:
            time.sleep(5)

    # Get the search results
    # Results limited to 10, the API does support paging
    response_dict = execute_mar_search_api(client,
        {
            "target": "/v1/" + search_id + "/results",
            "method": "GET",
            "parameters": {
                "$offset": 0,
                "$limit": 10,
                "filter": "",
                "sortBy": "count",
                "sortDirection": "desc"
            },
            "body": {}
        }
    )

    # Loop and display the results
    print "Results:"
    for result in response_dict['body']['items']:
        print "    " + result['output']['HostInfo|ip_address']