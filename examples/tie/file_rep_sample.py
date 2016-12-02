# This sample demonstrates invoking the McAfee Threat Intelligence Exchange
# (TIE) DXL service to retrieve the reputation of files (as identified
# by their hashes)

import logging
import os
import sys
import json
import base64

from dxlclient.client import DxlClient
from dxlclient.client_config import DxlClientConfig
from dxlclient.message import Message, Request

# Import common logging and configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from common import *

# Configure local logger
logging.getLogger().setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# The topic for requesting file reputations
FILE_REP_TOPIC = "/mcafee/service/tie/file/reputation"

# Create DXL configuration from file
config = DxlClientConfig.create_dxl_config_from_file(CONFIG_FILE)


def base64_from_hex(hexstr):
    """
    Returns the base64 string for the hex string specified

    :param hexstr: The hex string to convert to base64
    :return: The base64 value for the specified hes string
    """
    return base64.b64encode(hexstr.decode('hex'))


def get_tie_file_reputation(client, md5_hex, sha1_hex):
    """
    Returns a dictionary containing the results of a TIE file reputation request

    :param client: The DXL client
    :param md5_hex: The MD5 Hex string for the file
    :param sha1_hex: The SHA-1 Hex string for the file
    :return: A dictionary containing the results of a TIE file reputation request
    """
    # Create the request message
    req = Request(FILE_REP_TOPIC)

    # Create a dictionary for the payload
    payload_dict = {
        "hashes": [
            {"type": "md5", "value": base64_from_hex(md5_hex)},
            {"type": "sha1", "value": base64_from_hex(sha1_hex)}
        ]
    }

    # Set the payload
    req.payload = json.dumps(payload_dict).encode()

    # Send the request and wait for a response (synchronous)
    res = client.sync_request(req)

    # Return a dictionary corresponding to the response payload
    if res.message_type != Message.MESSAGE_TYPE_ERROR:
        return json.loads(res.payload.decode(encoding="UTF-8"))
    else:
        raise Exception("Error: " + res.error_message + " (" + str(res.error_code) + ")")

# Create the client
with DxlClient(config) as client:

    # Connect to the fabric
    client.connect()

    #
    # Request and display reputation for notepad.exe
    #
    response_dict = get_tie_file_reputation(client=client,
                                            md5_hex="f2c7bb8acc97f92e987a2d4087d021b1",
                                            sha1_hex="7eb0139d2175739b3ccb0d1110067820be6abd29")
    print "Notepad.exe reputation:"
    print json.dumps(response_dict, sort_keys=True, indent=4, separators=(',', ': ')) + "\n"

    #
    # Request and display reputation for EICAR
    #
    response_dict = get_tie_file_reputation(client=client,
                                            md5_hex="44d88612fea8a8f36de82e1278abb02f",
                                            sha1_hex="3395856ce81f2b7382dee72602f798b642f14140")
    print "EICAR reputation:"
    print json.dumps(response_dict, sort_keys=True, indent=4, separators=(',', ': '))
