# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2017 McAfee Inc. - All Rights Reserved.
################################################################################

import re

# This regex matches dotted-quad IPv4 addresses, like 123.123.123.123
REGEX_V4ADDR = re.compile(
    r"^(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])$")
# This monster matches all valid IPv6 addresses, including the embedded dotted-quad notation
# pylint: disable=line-too-long
REGEX_V6ADDR = re.compile(
    r"^(^(([0-9A-Fa-f]{1,4}(((:[0-9A-Fa-f]{1,4}){5}::[0-9A-Fa-f]{1,4})|((:[0-9A-Fa-f]{1,4}){4}::[0-9A-Fa-f]{1,4}(:[0-9A-Fa-f]{1,4}){0,1})|((:[0-9A-Fa-f]{1,4}){3}::[0-9A-Fa-f]{1,4}(:[0-9A-Fa-f]{1,4}){0,2})|((:[0-9A-Fa-f]{1,4}){2}::[0-9A-Fa-f]{1,4}(:[0-9A-Fa-f]{1,4}){0,3})|(:[0-9A-Fa-f]{1,4}::[0-9A-Fa-f]{1,4}(:[0-9A-Fa-f]{1,4}){0,4})|(::[0-9A-Fa-f]{1,4}(:[0-9A-Fa-f]{1,4}){0,5})|(:[0-9A-Fa-f]{1,4}){7}))$|^(::[0-9A-Fa-f]{1,4}(:[0-9A-Fa-f]{1,4}){0,6})$)|^::$)|^(^(([0-9A-Fa-f]{1,4}((((:[0-9A-Fa-f]{1,4}){4}:)|(:[0-9A-Fa-f]{1,4}){3}:(:[0-9A-Fa-f]{1,4}){0,1})|((:[0-9A-Fa-f]{1,4}){2}:(:[0-9A-Fa-f]{1,4}){0,2})|((:[0-9A-Fa-f]{1,4}):(:[0-9A-Fa-f]{1,4}){0,3})|(:(:[0-9A-Fa-f]{1,4}){0,4})|(:[0-9A-Fa-f]{1,4}){5}))|^(::[0-9A-Fa-f]{1,4}(:[0-9A-Fa-f]{1,4}){0,4}))|^:):((25[0-5]|2[0-4][0-9]|1[0-9]{2}|[0-9][0-9]|[0-9])\.){3}(25[0-5]|2[0-4][0-9]|[0-1]?[0-9]{0,2})$")
# This regex matches NetBIOS names (see http://support.microsoft.com/kb/909264)
REGEX_NETBIOS = re.compile(r"^([^\\/:*?\"<>|.]{1,15})$")
# This regex matches DNS names (see http://support.microsoft.com/kb/909264)
REGEX_FQDN = re.compile(
    r"^(([a-zA-Z0-9]|[a-zA-Z0-9][^\s,~:!@#$%\^&'\.\(\)\{\}_]*[^\s,~:!@#$%\^&'\.\(\)\{\}_\-])\.)*([a-zA-Z0-9]|[a-zA-Z0-9][^\s,~:!@#$%\^&'\.\(\)\{\}_]*[^\s,~:!@#$%\^&'\.\(\)\{\}_\-])$")


class ServerNameHelper(object):
    @staticmethod
    def is_valid_ip_address(ip_address):
        """
        Returns {@code True} if `ip_address` is a valid ipv4 or ipv6 ip address.

        :param ip_address: Address to validate.
        """
        return (ip_address is not None and ip_address != "" and (
            ServerNameHelper.is_valid_ipv4_address(ip_address) or ServerNameHelper.is_valid_ipv6_address(ip_address)))

    @staticmethod
    def is_valid_ipv4_address(ip_address):
        """
        Returns {@code True} if `ip_address` is a valid ipv4 ip address.

        :param ip_address: Address to validate.
        """
        return ip_address is not None and ip_address != "" and REGEX_V4ADDR.match(ip_address)

    @staticmethod
    def is_valid_ipv6_address(ip_address):
        """
        Returns {@code True} if `ip_address` is a valid ipv6 ip address.

        :param ip_address: Address to validate.
        """
        return ip_address is not None and ip_address != "" and REGEX_V6ADDR.match(ip_address)

    @staticmethod
    def is_valid_netbios_name(hostname):
        """
        Returns {@code True} if `hostname` is a valid NETBIOS name.

        :param hostname: Hostname to validate.
        """
        return hostname is not None and hostname != "" and REGEX_NETBIOS.match(hostname)

    @staticmethod
    def is_valid_fqdn(hostname):
        """
        Returns {@code True} if `hostname` is a valid FQDN.

        :param hostname: Hostname to validate.
        """
        return hostname is not None and hostname != "" and REGEX_FQDN.match(hostname)

    @staticmethod
    def is_valid_hostname_or_ipv4_address(hostname):  # pylint: disable=invalid-name
        """
        Returns {@code True} if `hostname` is a valid FQDN or a valid ipv4 address.

        :param hostname: Hostname to validate.
        """
        return (ServerNameHelper.is_valid_ipv4_address(hostname) or ServerNameHelper.is_valid_netbios_name(
            hostname) or ServerNameHelper.is_valid_fqdn(hostname))

    @staticmethod
    def is_valid_hostname_or_ip_address(hostname):
        """
        Returns {@code True} if `hostname` is a valid FQDN or a valid ipv4/ipv6 address.

        :param hostname: Hostname to validate.
        """
        return (ServerNameHelper.is_valid_ipv4_address(hostname) or ServerNameHelper.is_valid_ipv6_address(
            hostname) or ServerNameHelper.is_valid_netbios_name(hostname) or ServerNameHelper.is_valid_fqdn(hostname))
