# This sample demonstrates wrapping an existing service and exposing it on the
# DXL fabric.
#
# In this particular case, the "openweathermap.org" current weather data is
# exposed as a DXL service. This service wrapper delegates to the
# OpenWeatherMap REST API.

# The API key for invoking the weather service
API_KEY = "<obtain key from http://openweathermap.org/appid>"

# The name of the OpenWeatherMap service
SERVICE_NAME = "/openweathermap/service/openweathermap"

# The "current weather" topic
SERVICE_CURRENT_WEATHER_TOPIC = SERVICE_NAME + "/current"
