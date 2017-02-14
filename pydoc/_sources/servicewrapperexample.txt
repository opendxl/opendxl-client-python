Service Wrapper Sample
======================

Prior to running this sample make sure you have completed the samples configuration step (:doc:`sampleconfig`).

This sample demonstrates how simple it is to wrap an existing service and expose it on the DXL fabric.

In this particular case, the `OpenWeatherMap <http://openweathermap.org>`_ "current weather" data is exposed as a DXL service. This service
wrapper delegates to the `OpenWeatherMap REST API <http://openweathermap.org/api>`_.

OpenWeather API key
****************

Before running this sample you must obtain an "API key" from OpenWeatherMap:

    http://openweathermap.org/appid

Once you receive the API key, you must replace it in the ``openweather_common.py`` file as shown below:

    .. code-block:: python

        # The API key for invoking the weather service
        API_KEY = "01234567890123456789012345678901"

Service Wrapper
****************

The first step is to start the "service wrapper". This script will remain running and receive
:class:`dxlclient.message.Request` messages from clients that are querying weather information.

To start the "service wrapper", execute the ``sample\servicewrapper\openweather_service_wrapper.py`` script as follows:

    .. parsed-literal::

        c:\\dxlclient-python-sdk-\ |version|\>python sample\\servicewrapper\\openweather_service_wrapper.py

The output should appear similar to the following:

    .. code-block:: python

        2016-10-11 12:58:43,065 dxlclient.client - INFO - Waiting for broker list...
        2016-10-11 12:58:43,065 dxlclient.client - INFO - Checking brokers...
        2016-10-11 12:58:43,066 dxlclient.client - INFO - Trying to connect...
        2016-10-11 12:58:43,066 dxlclient.client - INFO - Trying to connect to broker {Unique id: {284bca2e-79e1-11e6-159d-005056812aa3}, Host name: 10.84.200.124, Port: 8883}...
        2016-10-11 12:58:43,315 dxlclient.client - INFO - Connected to broker {284bca2e-79e1-11e6-159d-005056812aa3}
        2016-10-11 12:58:43,315 dxlclient.client - INFO - Launching event loop...
        2016-10-11 12:58:43,316 dxlclient.client - INFO - Connected with result code 0
        2016-10-11 12:58:43,316 dxlclient.client - INFO - Subscribing to /mcafee/client/{5b18f1cc-adac-4f20-88d9-c23d9c531ada}
        2016-10-11 12:58:43,329 dxlclient.client - INFO - Message received for topic /mcafee/client/{5b18f1cc-adac-4f20-88d9-c23d9c531ada}
        2016-10-11 12:58:43,335 __main__ - INFO - Weather service is running...

The majority of code for the service wrapper is shown below:

    .. code-block:: python

        # The OpenWeatherMap "Current Weather" URL (see http://openweathermap.org/current)
        CURRENT_WEATHER_URL = "http://api.openweathermap.org/data/2.5/weather?{0}&APPID={1}"

        # The "current weather" topic
        SERVICE_CURRENT_WEATHER_TOPIC = "/openweathermap/service/openweathermap/current"

        # Create the client
        with DxlClient(config) as client:

            # Connect to the fabric
            client.connect()

            #
            # Register the service
            #

            # Create "Current Weather" incoming request callback
            class CurrentWeatherCallback(RequestCallback):
                def on_request(self, request):
                    try:
                        # Extract information from request
                        query = request.payload.decode(encoding="UTF-8")
                        logger.info("Service received request payload: " + query)

                        # Send HTTP request to OpenWeatherMap
                        req = urllib2.Request(
                            CURRENT_WEATHER_URL.format(query, API_KEY), None,
                            {'Content-Type': 'text/json'})
                        f = urllib2.urlopen(req)
                        weather_response = f.read()
                        f.close()

                        # Create the response message
                        response = Response(request)
                        # Populate the response payload
                        response.payload = weather_response.encode(encoding="UTF-8")
                        # Send the response
                        client.send_response(response)

                    except Exception as ex:
                        print str(ex)
                        # Send error response
                        client.send_response(ErrorResponse(request, error_message=str(ex).encode(encoding="UTF-8")))

            # Create service registration object
            info = ServiceRegistrationInfo(client, SERVICE_NAME)

            # Add a topic for the service to respond to
            info.add_topic(SERVICE_CURRENT_WEATHER_TOPIC, CurrentWeatherCallback())

            # Register the service with the fabric (wait up to 10 seconds for registration to complete)
            client.register_service_sync(info, 10)

            logger.info("Weather service is running...")

            # Wait forever
            while True:
                time.sleep(60)

The service wrapper registers a :class:`dxlclient.callbacks.RequestCallback` that will be invoked when
"current weather" query :class:`dxlclient.message.Request` messages are received.

The actual query (which can be weather by zip code, location, city, etc.) is extracted from the :class:`dxlclient.message.Request`
message's :attr:`dxlclient.message.Message.payload` attribute.

The `OpenWeatherMap REST API <http://openweathermap.org/api>`_ is invoked via HTTP with the query that was received in the DXL request
message's payload.

A DXL :class:`dxlclient.message.Response` message is created with a payload containing the result of invoking the
`OpenWeatherMap REST API <http://openweathermap.org/api>`_ and sent back to the invoking DXL client via
the :func:`dxlclient.client.DxlClient.send_response` method of the :class:`dxlclient.client.DxlClient` instance.

Service Invoker
***************

The next step is to execute the "service invoker". This script must be executed in a separate command prompt (or shell),
leaving the "service wrapper" running.

To start the "service invoker", execute the ``sample\servicewrapper\openweather_service_invoker.py`` script as follows:

    .. parsed-literal::

        c:\\dxlclient-python-sdk-\ |version|\>python sample\\servicewrapper\\openweather_service_invoker.py

The output should appear similar to the following (query for the current weather for zip code 97140):

    .. code-block:: python

        2016-10-11 13:20:50,565 dxlclient.client - INFO - Waiting for broker list...
        2016-10-11 13:20:50,566 dxlclient.client - INFO - Checking brokers...
        2016-10-11 13:20:50,568 dxlclient.client - INFO - Trying to connect...
        2016-10-11 13:20:50,569 dxlclient.client - INFO - Trying to connect to broker {Unique id: {284bca2e-79e1-11e6-159d-005056812aa3}, Host name: 10.84.200.124, Port: 8883}...
        2016-10-11 13:20:50,808 dxlclient.client - INFO - Connected to broker {284bca2e-79e1-11e6-159d-005056812aa3}
        2016-10-11 13:20:50,808 dxlclient.client - INFO - Launching event loop...
        2016-10-11 13:20:50,809 dxlclient.client - INFO - Connected with result code 0
        2016-10-11 13:20:50,809 dxlclient.client - INFO - Subscribing to /mcafee/client/{383105c5-17f7-4b40-bb90-7ed17bf3f315}
        2016-10-11 13:20:51,336 dxlclient.client - INFO - Message received for topic /mcafee/client/{383105c5-17f7-4b40-bb90-7ed17bf3f315}
        Client received response payload:
        {
            "base": "stations",
            "clouds": {
                "all": 0
            },
            "cod": 200,
            "coord": {
                "lat": 45.36,
                "lon": -122.84
            },
            "dt": 1476216689,
            "id": 5751632,
            "main": {
                "grnd_level": 1010.59,
                "humidity": 66,
                "pressure": 1010.59,
                "sea_level": 1034.15,
                "temp": 287.158,
                "temp_max": 287.158,
                "temp_min": 287.158
            },
            "name": "Sherwood",
            "sys": {
                "country": "US",
                "message": 0.171,
                "sunrise": 1476195849,
                "sunset": 1476235829
            },
            "weather": [
                {
                    "description": "clear sky",
                    "icon": "01d",
                    "id": 800,
                    "main": "Clear"
                }
            ],
            "wind": {
                "deg": 83.0013,
                "speed": 3.1
            }
        }


The majority of code for the service invoker is shown below:

    .. code-block:: python

        # The "current weather" topic
        SERVICE_CURRENT_WEATHER_TOPIC = "/openweathermap/service/openweathermap/current"

        # Create the "Current Weather" request
        req = Request(SERVICE_CURRENT_WEATHER_TOPIC)
        # Populate the request payload
        # Examples include:
        #   By ZIP code: zip=97140,us
        #   By geographic coordinates: lat=35&lon=139
        #   By city name: q=London,uk
        req.payload = "zip=97140,us".encode()

        # Send the request and wait for a response (synchronous)
        res = client.sync_request(req)

        # Extract information from the response (if an error did not occur)
        if res.message_type != Message.MESSAGE_TYPE_ERROR:
            response_dict = json.loads(res.payload.decode(encoding="UTF-8"))
            print "Client received response payload: \n" + \
              json.dumps(response_dict, sort_keys=True, indent=4, separators=(',', ': '))
        else:
            logger.error("Error: " + res.error_message + " (" + str(res.error_code) + ")")

A DXL :class:`dxlclient.message.Request` message is created and its payload is set to the query (zip code,
location, city, etc.) to perform against the `OpenWeatherMap REST API <http://openweathermap.org/api>`_.

A synchronous request is sent to the DXL service via the :func:`dxlclient.client.DxlClient.sync_request` method of
the :class:`dxlclient.client.DxlClient` instance.

The results of the query are extracted from the :class:`dxlclient.message.Response` that was received and displayed.

