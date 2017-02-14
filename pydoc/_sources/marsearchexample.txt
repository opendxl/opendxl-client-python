McAfee Active Response (MAR) Search Sample
=========================================================

This sample queries McAfee Active Response for the IP addresses of hosts that have an ``Active Response`` client
installed.

Prerequisites
*************
* The samples configuration step has been completed (:doc:`sampleconfig`)
* A McAfee Active Response (MAR) Service is available on the DXL fabric
* The python client has been authorized to perform MAR searches (see :doc:`marsendauth`)

To run this sample execute the ``sample\mar\search_example.py`` script as follows:

    .. parsed-literal::

        c:\\dxlclient-python-sdk-\ |version|\>python sample\\mar\\search_example.py

To perform an Active Response query via DXL the following steps must be performed:

* Create a MAR search by sending a search query (via a :class:`dxlclient.message.Request` message) to the MAR service
* Extract the search identifier from the :class:`dxlclient.message.Response` message received in response to the query creation request
* Start the search by sending an appropriate :class:`dxlclient.message.Request` message to the MAR service
* Poll the MAR service for the status of the search by sending :class:`dxlclient.message.Request` messages to obtain the search status (via :class:`dxlclient.message.Response` messages)
* Once the search has completed, query the MAR service for the results of the search (via a :class:`dxlclient.message.Request` message)
* Process the results of the search query in the :class:`dxlclient.message.Response` message received corresponding to the results request

All of the MAR query-related :class:`dxlclient.message.Request` messages described in the steps above are sent to the same DXL topic (``/mcafee/mar/service/api/search``).

Each of these steps are performed in the sample script and will be described in detail throughout the rest of this
document. All of the steps utilize a local convenience method within the script (``execute_mar_search_api()``).
This method is responsible for hiding the details of converting Python ``dictionary`` objects to DXL request objects
and extracting dictionaries from DXL response objects. The method also hides the details of sending synchronous
requests to the MAR service and handling any errors that may occur. The ``execute_mar_search_api()`` method is
described in detail at the bottom of this document.

The first step is to create a MAR query as shown below. In this particular case the query will be for the IP
addresses (``ip_address``) of any hosts (``HostInfo``) that have an Active Response client installed.

    .. code-block:: python

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

As shown below, the code block above results in a :class:`dxlclient.message.Request` message being sent to the
MAR service containing the query that is to be created. The :class:`dxlclient.message.Response` message from the MAR
service includes meta-information about the search that was created, including a status code (``code``) with a
value of 201 (``created``) indicating that the creation was successful along with the identifier (``id``) of the
search (this identifier will be used in subsequent steps).

    .. code-block:: python

        Request:

        {
            "body": {
                "aggregated": true,
                "projections": [
                    {
                        "name": "HostInfo",
                        "outputs": [
                            "ip_address"
                        ]
                    }
                ]
            },
            "method": "POST",
            "parameters": {},
            "target": "/v1/simple"
        }

        Response:

        {
            "body": {
                "aggregated": true,
                "catalogVersion": 0,
                "createdAt": 1474308184842,
                "dbVersion": 0,
                "expectedHostResponses": 0,
                "id": "57e02858e4b0217da8f65e80",
                "invalid": false,
                "projections": [ ... ],
                "running": false,
                "status": "CREATED",
                "temporal": true,
                "ttl": 60000
            },
            "code": 201
        }

The next step (as shown below) extracts the identifier (``id``) of the newly created search from the response
dictionary. This identifier is included in the next request that is sent to the MAR service requesting that
the search be started.

    .. code-block:: python

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


As shown below, the code block above results in a :class:`dxlclient.message.Request` message being sent to the
MAR service requesting that the search be started. The :class:`dxlclient.message.Response` message from the MAR
service includes a status code (``code``) with a value of 200 (``OK``) indicating that the search has been started.

    .. code-block:: python

        Request:

        {
            "body": {},
            "method": "PUT",
            "parameters": {},
            "target": "/v1/57e02858e4b0217da8f65e80/start"
        }

        Response:

        {
            "body": {
                "aggregated": true,
                "catalogVersion": 1,
                "createdAt": 1474308184842,
                "dbVersion": 2,
                "executedAt": 1474308184964,
                "expectedHostResponses": 1,
                "id": "57e02858e4b0217da8f65e80",
                "invalid": false,
                "projections": [ ... ],
                "running": false,
                "startTime": 1474308184964,
                "status": "STARTED",
                "temporal": true,
                "ttl": 60000
            },
            "code": 200
        }

The next step (as shown below) will poll the MAR service for the status of the executed search until it has reached a
status of ``FINISHED``.

    .. code-block:: python

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

As shown below, the code block above results in one or more :class:`dxlclient.message.Request` messages being sent to
the MAR service requesting the status of the search. Each :class:`dxlclient.message.Response` message from the MAR
service includes the current status (``status``) of the search (``STARTED``, ``FINISHED``, etc.).

    .. code-block:: python

        Request:

        {
            "body": {},
            "method": "GET",
            "parameters": {},
            "target": "/v1/57e02858e4b0217da8f65e80/status"
        }

        Response:

        {
            "body": {
                "errors": 0,
                "hosts": 0,
                "results": 0,
                "status": "STARTED",
                "subscribedHosts": 0
            },
            "code": 200
        }

        Request:

        {
            "body": {},
            "method": "GET",
            "parameters": {},
            "target": "/v1/57e02858e4b0217da8f65e80/status"
        }

        Response:

        {
            "body": {
                "errors": 0,
                "hosts": 1,
                "results": 1,
                "status": "FINISHED",
                "subscribedHosts": 1
            },
            "code": 200
        }

Once the search has completed, the next step is to obtain the results of the search from the MAR service (as shown
in the code block below). In this particular case, the search results are being limited (``$limit``) to 10 results.

    .. code-block:: python

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

As shown below, the code block above sends a :class:`dxlclient.message.Request` message to the MAR service
indicating how results are to be received (filtered, sorted, limited, etc.). The corresponding
:class:`dxlclient.message.Response` message includes the search results (``items``) along with meta-information
about the results (counts, paging-related information, etc.).

    .. code-block:: python

        Request:

        {
            "body": {},
            "method": "GET",
            "parameters": {
                "$limit": 10,
                "$offset": 0,
                "filter": "",
                "sortBy": "count",
                "sortDirection": "desc"
            },
            "target": "/v1/57e02858e4b0217da8f65e80/results"
        }

        Response:

        {
            "body": {
                "currentItemCount": 1,
                "items": [
                    {
                        "count": 1,
                        "created_at": "2016-09-19T18:03:07.722Z",
                        "id": "{1=[10.84.200.99]}",
                        "output": {
                            "HostInfo|ip_address": "10.84.200.99"
                        }
                    }
                ],
                "itemsPerPage": 10,
                "startIndex": 0,
                "totalItems": 1
            },
            "code": 200
        }


The final code block in the script extracts the IP addresses from the search results (as shown below).

    .. code-block:: python

        # Loop and display the results
        print "Results:"
        for result in response_dict['body']['items']:
            print "    " + result['output']['HostInfo|ip_address']

The output should appear similar to the following:

    .. code-block:: python

        Results:
            10.84.200.99

The major functionality provided by this sample resides in the ``execute_mar_search_api()`` method as shown
below:

    .. code-block:: python

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

This method creates a :class:`dxlclient.message.Request` message that will be delivered to the
search topic (``/mcafee/mar/service/api/search``) of a MAR service on the fabric. Prior to delivering the request,
the dictionary specified as a method parameter (``payload_dict``) is converted to a JSON string and
placed in the payload of the request message.

The request message is delivered to the fabric via the :func:`dxlclient.client.DxlClient.sync_request` method on
the DXL client.

The payload of the :class:`dxlclient.message.Response` message received is converted to a Python ``dictionary``
object. The status code (``code``) within the dictionary is examined to ensure that the request was successful.
If the request was successful, the dictionary extracted from the response is returned to the caller of the method.
The method will raise exceptions for any errors that occur during the request itself or during validation.
