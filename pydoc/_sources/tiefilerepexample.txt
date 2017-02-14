Threat Intelligence Exchange (TIE) File Reputation Sample
=========================================================

This sample demonstrates invoking the McAfee Threat Intelligence Exchange
(TIE) DXL service to retrieve the reputation of files (as identified
by their hashes).

Prerequisites
*************
* The samples configuration step has been completed (:doc:`sampleconfig`)
* A TIE Service is available on the DXL fabric

To run this sample execute the ``sample\tie\file_rep_sample.py`` script as follows:

    .. parsed-literal::

        c:\\dxlclient-python-sdk-\ |version|\>python sample\\tie\\file_rep_sample.py

The output should appear similar to the following:

    .. code-block:: python

        Notepad.exe reputation:
        {
            "props": {
                "serverTime": 1451505556,
                "submitMetaData": 1
            },
            "reputations": [
                {
                    "attributes": {
                        "2120340": "2139160704"
                    },
                    "createDate": 1451502875,
                    "providerId": 1,
                    "trustLevel": 99
                },
                {
                    "attributes": {
                        "2101652": "17",
                        "2102165": "1451502875",
                        "2111893": "21",
                        "2114965": "0",
                        "2139285": "72339069014638857"
                    },
                    "createDate": 1451502875,
                    "providerId": 3,
                    "trustLevel": 0
                }
            ]
        }

        EICAR reputation:
        {
            "props": {
                "serverTime": 1451505556,
                "submitMetaData": 1
            },
            "reputations": [
                {
                    "attributes": {
                        "2120340": "2139162632"
                    },
                    "createDate": 1451504331,
                    "providerId": 1,
                    "trustLevel": 1
                },
                {
                    "attributes": {
                        "2101652": "11",
                        "2102165": "1451504331",
                        "2111893": "22",
                        "2114965": "0",
                        "2139285": "72339069014638857"
                    },
                    "createDate": 1451504331,
                    "providerId": 3,
                    "trustLevel": 0
                }
            ]
        }

The sample outputs the file reputation for two files.

The first file queried in the TIE service is "notepad.exe". The McAfee Global Threat Intelligence (GTI) service
is identified in the results as ``"providerId" : 1``. The trust level associated with the GTI response
(``"trustLevel": 99``) indicates that the file is known good.

The second file queried in the TIE service is the "EICAR Standard Anti-Virus Test File". The trust level associated
with the GTI response (``"trustLevel": 1``) indicates that the file is known bad.

The major functionality provided by the sample resides in the ``get_tie_file_reputation()`` method as shown
below:

    .. code-block:: python

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
                "agentGuid" : "myagent",
                "hashes" : [
                    { "type" : "md5", "value" : base64_from_hex(md5_hex) },
                    { "type" : "sha1", "value" : base64_from_hex(sha1_hex) }
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

This method creates a :class:`dxlclient.message.Request` message that will be delivered to the
file reputation request topic (``/mcafee/service/tie/file/reputation``) of a TIE service on the fabric.

The required payload for a "TIE File Reputation" request is set on the message.

The request message is delivered to the fabric via the :func:`dxlclient.client.DxlClient.sync_request` method on
the DXL client.

The payload of the :class:`dxlclient.message.Response` message received is converted to a Python ``dictionary``
object and returned to the caller of the method.
