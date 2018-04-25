# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
###############################################################################

"""Helpers for making requests to a Management Service for CLI subcommands"""

from __future__ import absolute_import
import json
import logging
import warnings
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class ManagementService(object):
    """
    Handles REST invocation of Management Service
    """
    # pylint: disable=too-many-arguments
    def __init__(self, host, port, username, password, verify):
        """
        Constructor parameters:

        :param str host: the hostname of the Management Service to run remote
            commands on
        :param str port: the port of the desired Management Service
        :param str username: the username to run the remote commands as
        :param str password: the password for the Management Service user
        :param verify: If the value is a `bool`, the value specifies whether or
            not to verify the Management Service"s certificate. If the value
            is a `str`, the value specifies the location of a file of CA
            certificates to use when verifying the Management Service"s
            certificate.
        :type verify: bool or str
        """
        self._host = host
        self._port = port
        self._base_url = "https://{}:{}/remote".format(host, port)
        self._port = port
        self._auth = HTTPBasicAuth(username, password)
        self._session = requests.Session()
        self._verify = verify

    def invoke_command(self, command_name, params=None):
        """
        Invokes the given remote command by name with the supplied parameters

        :param str command_name: The name of the Management Service remote
            command to invoke
        :param dict params: Parameters to pass to the remote command
        :return: the response for the Management Service remote command
        :rtype: str or unicode
        """
        params = params if params is not None else {}
        params[":output"] = "json"
        request_target = "{}:{}/{}".format(self._host, self._port,
                                           command_name)
        return self._parse_response(self._send_request(command_name, params),
                                    request_target)

    def _send_request(self, command_name, params=None):
        """
        Sends a request to the Management Service with the supplied command
        name and parameters

        :param str command_name: The command name to invoke
        :param dict params: The parameters to provide for the command
        :return: the response object from Management Service
        :rtype: requests.Response
        """
        _request_url = "{}/{}".format(self._base_url, command_name)
        logger.debug("Invoking request %s with the following parameters:",
                     _request_url)
        logger.debug(params)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", ".*subjectAltName.*")
            if not self._verify:
                warnings.filterwarnings("ignore", "Unverified HTTPS request")
            return self._session.get(_request_url,
                                     auth=self._auth,
                                     params=params,
                                     verify=self._verify)

    @staticmethod
    def _parse_response(response, request_target):
        """
        Parses the response object from Management Service. Removes the
        return status and code from the response body and returns just the
        JSON-decoded remote command response. Raises an exception if an error
        response is returned.

        :param requests.Response response: the Management Service remote
            command response object to parse
        :return: the Management Service remote command results
        :rtype: str
        :raise Exception: if the service returns a non-200 status code or the
            first line in the response has text other than "OK:"
        """
        response_body = response.text
        status_code = response.status_code

        logger.debug("Response: %s", response_body)
        if status_code != 200:
            raise Exception(
                "Request to {} failed with HTTP error code: {}. Reason: {}".
                format(request_target, status_code, response.reason))

        if ":" not in response_body:
            raise Exception(
                "Did not find ':' status delimiter in response body")

        response_status_delimiter = response_body.index(":")
        status = response_body[:response_status_delimiter]
        response_detail = response_body[response_status_delimiter+1:].strip()

        if status != "OK":
            raise Exception(
                "Request to {} failed with status: {}. Message: {}".format(
                    request_target, status.strip(), response_detail))

        return json.loads(response_detail)
