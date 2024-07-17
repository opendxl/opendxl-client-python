# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
###############################################################################

"""
Test cases for the CLI subcommands (generatecsr, provisionconfig, and
updateconfig.
"""

# Run with nosetests dxlclient.test.test_cli

from __future__ import absolute_import
from __future__ import print_function
import base64
import datetime
from datetime import timedelta
from datetime import tzinfo
import getpass
import json
import os
import shutil
import sys
import tempfile
import unittest
import uuid

if sys.version_info[0] > 2:
    from io import StringIO as NativeStringIO
else:
    from io import BytesIO as NativeStringIO

# pylint: disable=wrong-import-position
from asn1crypto import csr, pem, x509, algos
from mock import call, patch
from parameterized import parameterized
import requests_mock
from oscrypto import asymmetric

from dxlclient import DxlUtils
from dxlclient._cli import cli_run

from .base_test import builtins

# pylint: disable=missing-docstring


def command_args(args):
    arg_list = list(args) if isinstance(args, (list, tuple)) else [args]
    return ["command"] + arg_list


class _TempDir(object):
    def __init__(self, prefix, delete_on_exit=True):
        self.prefix = prefix
        self.dir = None
        self.delete_on_exit = delete_on_exit

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="{}_".format(self.prefix))
        return self.dir

    def __exit__(self, exception_type, exception_value, traceback):
        if self.delete_on_exit and self.dir:
            shutil.rmtree(self.dir)


class _CertificateRequest(object):
    def __init__(self, csr_file):
        csr_bytes = slurp_file_into_bytes(csr_file)
        _, _, der_bytes = pem.unarmor(csr_bytes)
        self.request = csr.CertificationRequest.load(der_bytes)

    @property
    def subject(self):
        return self.request["certification_request_info"]["subject"].native

    @property
    def subject_alt_names(self):
        names = None

        attributes = self.request["certification_request_info"]["attributes"]
        extension_request = next((attribute for attribute in attributes
                                  if attribute["type"].native ==
                                  "extension_request"), None)
        if extension_request:
            san_extension = None
            for extensions in extension_request["values"]:
                san_extension = next(
                    (extension for extension in extensions
                     if extension["extn_id"].native == "subject_alt_name"),
                    None)
                if san_extension:
                    break

            if san_extension:
                names = [name.native
                         for name in san_extension["extn_value"].parsed]
        return names


class _PrivateKey(object):
    def __init__(self, private_key_file, password=None):
        private_key_bytes = slurp_file_into_bytes(private_key_file)
        self.private_key = asymmetric.load_private_key(private_key_bytes,
                                                       password)

    @property
    def algorithm(self):
        return self.private_key.algorithm


def get_fake_public_key_asn1():
    fake_public_key, _ = asymmetric.generate_pair("rsa", 1024)
    return fake_public_key.asn1


_SIGNATURE_ALGORITHM = algos.SignedDigestAlgorithm({
    "algorithm": u"sha256_rsa"})
_FAKE_SUBJECT = x509.Name.build({u"common_name": u"fake"})

# for adding a timezone to datetime objects
ZERO = timedelta(0)

# A UTC class.
class UTC(tzinfo):
    """UTC"""

    def utcoffset(self, _unused):
        return ZERO

    def tzname(self, _unused):
        return "UTC"

    def dst(self, _unused):
        return ZERO

UTC = UTC()

FAKE_CERTIFICATE = \
    pem.armor(u"CERTIFICATE",
              x509.Certificate({
                  "tbs_certificate": x509.TbsCertificate({
                      "version": 1,
                      "serial_number": 1,
                      "signature": _SIGNATURE_ALGORITHM,
                      "issuer": _FAKE_SUBJECT,
                      "validity": {
                          "not_before": x509.Time(
                              name="utc_time",
                              value=datetime.datetime(2000, 1, 1, 9, 47, 35, 249000, tzinfo=UTC)),
                          "not_after": x509.Time(
                              name="utc_time",
                              value=datetime.datetime(2049, 12, 31, 9, 47, 35, 249000, tzinfo=UTC))},
                      "subject": _FAKE_SUBJECT,
                      "subject_public_key_info":
                          get_fake_public_key_asn1()}),
                  "signature_algorithm": algos.SignedDigestAlgorithm({
                      "algorithm": u"sha256_rsa"}),
                  "signature_value": b"fake"}).dump()).decode('utf8')

FAKE_CSR = \
    pem.armor(
        u"CERTIFICATE REQUEST",
        csr.CertificationRequest({
            "certification_request_info":
                csr.CertificationRequestInfo({
                    "version": 1,
                    "subject": _FAKE_SUBJECT,
                    "subject_pk_info": get_fake_public_key_asn1()}),
            "signature_algorithm": _SIGNATURE_ALGORITHM,
            "signature": b"fake"}).dump()).decode('utf8')


class CliTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        patch.stopall()

    @parameterized.expand([
        ([],),
        ("-h",),
        ("--help",)
    ])
    def test_help_command(self, value):
        with patch("dxlclient._cli.argparse.ArgumentParser.print_help") \
                as print_help, \
                patch("sys.argv", new=command_args(value)), \
                self.assertRaises(SystemExit) as context:
            cli_run()
        self.assertEqual(1, print_help.call_count)
        self.assertEqual(0, context.exception.code)

    @parameterized.expand([
        ("invalid",),
        ("",),
        ("?",)])
    def test_invalid_args_returns_error_code(self, value):
        stderr_bytes = NativeStringIO()
        with patch("dxlclient._cli.argparse.ArgumentParser.print_help"), \
                patch("sys.argv", command_args(value)), \
                patch("sys.stderr", new=stderr_bytes), \
                self.assertRaises(SystemExit) as context:
            cli_run()
        stderr_bytes.seek(0)
        stderr_string = stderr_bytes.read()
        self.assertIn("invalid choice", stderr_string)
        self.assertNotEqual(0, context.exception.code)

    @parameterized.expand([
        ("client1",),
        (["client2", "-f", "client3"],)
    ])
    def test_generatecsr_basic(self, value):
        if isinstance(value, list):
            common_name, _, file_prefix = value
            client_args = value
        else:
            common_name = value
            file_prefix = "client"
            client_args = [value]

        with _TempDir("gencsr_basic") as temp_dir, \
                patch("sys.argv", command_args(["generatecsr", temp_dir]
                                               + client_args)):
            cli_run()

            # Validate csr was created properly
            csr_file = os.path.join(temp_dir, "{}.csr".format(file_prefix))
            self.assertTrue(os.path.exists(csr_file))
            request = _CertificateRequest(csr_file)
            self.assertDictEqual({"common_name": common_name}, request.subject)

            # Validate private key was created properly
            private_key_file = os.path.join(temp_dir, "{}.key".format(
                file_prefix))
            self.assertTrue(os.path.exists(private_key_file))
            key = _PrivateKey(private_key_file)
            self.assertEqual("rsa", key.algorithm)

    def test_generatecsr_with_full_subject(self):
        with _TempDir("gencsr_fs") as temp_dir, \
                patch("sys.argv", command_args(["generatecsr",
                                                temp_dir,
                                                "myclient",
                                                "--country", "US",
                                                "--state-or-province", "OR",
                                                "--locality", "Hillsboro",
                                                "--organization", "McAfee",
                                                "--organizational-unit",
                                                "DXL Team"])):
            cli_run()

            csr_file = os.path.join(temp_dir, "client.csr")
            self.assertTrue(os.path.exists(csr_file))
            request = _CertificateRequest(csr_file)
            self.assertDictEqual({"common_name": "myclient",
                                  "country_name": "US",
                                  "state_or_province_name": "OR",
                                  "locality_name": "Hillsboro",
                                  "organization_name": "McAfee",
                                  "organizational_unit_name": "DXL Team"},
                                 request.subject)

    def test_generatecsr_with_subject_alt_names(self):
        with _TempDir("gencsr_sans") as temp_dir, \
                patch("sys.argv",
                      command_args([
                          "generatecsr",
                          temp_dir,
                          "myclient",
                          "-s", "host1.com", "host2.com"])):
            cli_run()

            csr_file = os.path.join(temp_dir, "client.csr")
            self.assertTrue(os.path.exists(csr_file))
            request = _CertificateRequest(csr_file)
            self.assertEqual(["host1.com", "host2.com"],
                             request.subject_alt_names)

    def test_generatecsr_with_encrypted_private_key_and_passphrase_arg(self):
        with _TempDir("gencsr_enc_pk_pass_arg") as temp_dir, \
                patch("sys.argv", command_args(["generatecsr",
                                                temp_dir,
                                                "myclient",
                                                "-P", "itsasecret"])):
            cli_run()

            private_key_file = os.path.join(temp_dir, "client.key")
            self.assertTrue(os.path.exists(private_key_file))

            # Validate that supplying no password raises an exception
            self.assertRaises((ValueError, OSError), _PrivateKey,
                              private_key_file)

            # Validate that supplying a bad password raises an exception
            self.assertRaises((ValueError, OSError), _PrivateKey,
                              private_key_file, "wrongpass")

            # Validate that supplying the right password is successful
            key = _PrivateKey(private_key_file, "itsasecret")
            self.assertEqual("rsa", key.algorithm)

    def test_generatecsr_with_encrypted_private_key_and_passphrase_prompt(self):
        passphrase = "itsasecret"

        responses = ['', passphrase + "nomatch1", passphrase + "nomatch2",
                     passphrase, passphrase]
        response_count = [-1]
        def prompt_response(_):
            response_count[0] += 1
            return responses[response_count[0]]

        with _TempDir("gencsr_enc_pk_pass_prompt") as temp_dir,\
                patch("sys.argv", command_args(["generatecsr",
                                                temp_dir,
                                                "myclient",
                                                "-P"])), \
                patch.object(builtins, 'print') as mock_print, \
                patch.object(getpass, "getpass",
                             side_effect=prompt_response) as mock_getpass:
            cli_run()

            mock_getpass.assert_has_calls([
                call("Enter private key passphrase:"),
                call("Enter private key passphrase:"),
                call("Confirm private key passphrase:"),
                call("Enter private key passphrase:"),
                call("Confirm private key passphrase:")
            ])

            mock_print.assert_has_calls([
                call("Value cannot be empty. Try again."),
                call("Values for private key passphrase do not match. Try again.")
            ])

            private_key_file = os.path.join(temp_dir, "client.key")
            self.assertTrue(os.path.exists(private_key_file))

            # Validate that supplying no password raises an exception
            self.assertRaises((ValueError, OSError), _PrivateKey,
                              private_key_file)

            # Validate that supplying a bad password raises an exception
            self.assertRaises((ValueError, OSError), _PrivateKey,
                              private_key_file, "wrongpass")

            # Validate that supplying the right password is successful
            key = _PrivateKey(private_key_file, "itsasecret")
            self.assertEqual("rsa", key.algorithm)

    @parameterized.expand([
        ("client",),
        (["client2", "-f", "client3"],)
    ])
    def test_provisionconfig_basic(self, value):
        if isinstance(value, list):
            common_name, _, file_prefix = value
            client_args = value
        else:
            common_name = value
            file_prefix = "client"
            client_args = [value]

        with _TempDir("provconfig_basic") as temp_dir, \
                patch("sys.argv", command_args(["provisionconfig",
                                                temp_dir,
                                                "myhost"]
                                               + client_args
                                               + ["-u", "myuser",
                                                  "-p", "mypass"])),\
                requests_mock.mock(case_sensitive=True) as req_mock:
            ca_bundle_for_response = make_fake_ca_bundle()
            client_cert_for_response = FAKE_CERTIFICATE
            brokers_for_response = make_broker_lines()
            req_mock.get(get_server_provision_url("myhost"),
                         text=get_mock_provision_response_func(
                             ca_bundle_for_response,
                             client_cert_for_response,
                             broker_lines_for_server_response(
                                 brokers_for_response)))

            cli_run()

            # Validate csr was created properly
            csr_file = os.path.join(temp_dir, "{}.csr".format(file_prefix))
            self.assertTrue(os.path.exists(csr_file))
            request = _CertificateRequest(csr_file)
            self.assertDictEqual({"common_name": common_name}, request.subject)

            # Validate private key was created properly
            private_key_file = os.path.join(temp_dir, "{}.key".format(
                file_prefix))
            self.assertTrue(os.path.exists(private_key_file))
            key = _PrivateKey(private_key_file)
            self.assertEqual("rsa", key.algorithm)

            self.assertEqual(1, len(req_mock.request_history))
            request = req_mock.request_history[0]

            # Validate auth credentials sent in request
            expected_creds = "Basic {}".format(base64.b64encode(
                b"myuser:mypass").decode("utf8"))
            self.assertEqual(expected_creds, request.headers["Authorization"])

            # Validate csr saved to disk matches csr submitted for signing
            csr_bytes_from_file = slurp_file_into_bytes(csr_file)
            csr_bytes_in_request = flattened_query_params(request).get(
                "csrString")
            self.assertEqual(csr_bytes_in_request.encode("utf8"),
                             csr_bytes_from_file)

            # Validate CA bundle returned for request matches stored file
            ca_bundle_file = os.path.join(temp_dir, "ca-bundle.crt")
            self.assertTrue(os.path.exists(ca_bundle_file))
            ca_bundle_from_file = slurp_file_into_bytes(ca_bundle_file)
            self.assertEqual(ca_bundle_for_response.encode("utf8"),
                             ca_bundle_from_file)

            # Validate client cert returned for request matches stored file
            client_cert_file = os.path.join(temp_dir, "{}.crt".format(
                file_prefix))
            self.assertTrue(os.path.exists(client_cert_file))
            client_cert_from_file = slurp_file_into_bytes(client_cert_file)
            self.assertEqual(client_cert_for_response.encode("utf8"),
                             client_cert_from_file)

            # Validate config file stored properly, with broker data returned
            # from server
            expected_config_content = make_config(
                make_basic_config(client_prefix=file_prefix),
                broker_lines_for_config_file(brokers_for_response))

            config_file = os.path.join(temp_dir, "dxlclient.config")
            self.assertTrue(os.path.exists(config_file))
            config_from_file = slurp_file_into_bytes(config_file)
            self.assertEqual(expected_config_content, config_from_file)

    def test_provisionconfig_with_csr(self):
        csr_file = "myclient.csr"
        with _TempDir("provconfig_csr") as temp_dir, \
                patch("sys.argv", command_args(["provisionconfig",
                                                temp_dir,
                                                "myhost",
                                                os.path.join(temp_dir,
                                                             csr_file),
                                                "-u", "myuser",
                                                "-p", "mypass",
                                                "-r"])), \
                requests_mock.mock(case_sensitive=True) as req_mock:
            client_cert_for_response = FAKE_CERTIFICATE
            csr_to_test = FAKE_CSR
            full_csr_file_path = os.path.join(temp_dir, csr_file)
            DxlUtils.save_to_file(full_csr_file_path, csr_to_test)
            req_mock.get(get_server_provision_url("myhost"),
                         text=get_mock_provision_response_func(
                             client_cert=client_cert_for_response))

            cli_run()

            self.assertEqual(1, len(req_mock.request_history))
            request = req_mock.request_history[0]

            # Validate csr saved to disk was not regenerated and matches csr
            # submitted for signing
            csr_bytes_from_file = slurp_file_into_bytes(full_csr_file_path)
            csr_bytes_in_request = flattened_query_params(request).get(
                "csrString")
            self.assertEqual(csr_bytes_in_request.encode("utf8"),
                             csr_bytes_from_file)
            self.assertEqual(csr_to_test.encode("utf8"),
                             csr_bytes_from_file)

            # Validate client cert returned for request matches stored file
            client_cert_file = os.path.join(temp_dir, "client.crt")
            self.assertTrue(os.path.exists(client_cert_file))
            client_cert_from_file = slurp_file_into_bytes(client_cert_file)
            self.assertEqual(client_cert_for_response.encode("utf8"),
                             client_cert_from_file)

    def test_provisionconfig_with_trusted_ca_cert_and_port(self):
        with _TempDir("provconfig_ca_port") as temp_dir, \
                patch("sys.argv", command_args(["provisionconfig",
                                                temp_dir,
                                                "myhost",
                                                "myclient",
                                                "-t", "58443",
                                                "-u", "myuser",
                                                "-p", "mypass",
                                                "-e", "mytruststore.pem"])), \
                requests_mock.mock(case_sensitive=True) as req_mock:
            req_mock.get(get_server_provision_url("myhost", 58443),
                         text=get_mock_provision_response_func())

            cli_run()

            self.assertEqual(1, len(req_mock.request_history))
            request = req_mock.request_history[0]

            self.assertEqual("mytruststore.pem", request.verify)

    def test_provisionconfig_with_prompt_for_server_user_and_password(self):
        responses = {"Enter server username:": "myuser",
                     "Enter server password:": "mypass"}
        def prompt_response(arg):
            return responses[arg]

        with _TempDir("provconfig_no_server_creds") as temp_dir, \
                patch("sys.argv", command_args(["provisionconfig",
                                                temp_dir,
                                                "myhost",
                                                "myclient"])), \
                patch.object(getpass, "getpass",
                             side_effect=prompt_response) as mock_getpass, \
                requests_mock.mock(case_sensitive=True) as req_mock:
            req_mock.get(get_server_provision_url("myhost", 8443),
                         text=get_mock_provision_response_func())

            cli_run()

            self.assertEqual(1, len(req_mock.request_history))
            request = req_mock.request_history[0]

            # Validate auth credentials sent in request
            expected_creds = "Basic {}".format(base64.b64encode(
                b"myuser:mypass").decode("utf8"))
            self.assertEqual(expected_creds, request.headers["Authorization"])

            self.assertEqual(2, mock_getpass.call_count)


    def test_updateconfig_basic(self):
        with _TempDir("updateconfig_basic") as temp_dir, \
                patch("sys.argv", command_args(["updateconfig",
                                                temp_dir,
                                                "myhost",
                                                "-u", "myuser",
                                                "-p", "mypass"])), \
                requests_mock.mock(case_sensitive=True) as req_mock:
            base_broker_lines = broker_lines_for_config_file(
                make_broker_lines(2), add_comments=True)
            base_config_lines = make_basic_config(
                ca_bundle_file="mycabundle.pem",
                add_comments=True)
            base_config_content = make_config(base_config_lines,
                                              base_broker_lines,
                                              add_general=False)

            # Before the broker config update is done, there should be entries
            # for broker1 and broker2. The updated config contains entries for
            # broker2 (pre-existing), broker3 (new), and broker4 (new). broker1
            # is expected to be deleted from the config on disk during the
            # update. The comment line above the entry for broker2 in the
            # config file should be preserved after the update.
            updated_brokers = make_broker_dict(4)
            del updated_brokers["brokers"][0]
            updated_brokers["webSocketBrokers"] = updated_brokers["brokers"]
            expected_brokers = make_broker_lines(4)
            del expected_brokers[0]
            expected_broker_lines = "# This is broker 2\n{}".format(
                broker_lines_for_config_file(expected_brokers))
            expected_config_content = make_config(base_config_lines,
                                                  expected_broker_lines,
                                                  add_general=False)

            ca_bundle_file = os.path.join(temp_dir, "mycabundle.pem")
            DxlUtils.save_to_file(ca_bundle_file, "old ca")
            updated_ca_bundle = make_fake_ca_bundle(2)

            config_file = os.path.join(temp_dir, "dxlclient.config")
            DxlUtils.save_to_file(config_file, base_config_content)

            req_mock.get(get_server_client_ca_url("myhost"),
                         text=get_mock_ca_bundle_response_func(
                             updated_ca_bundle))
            req_mock.get(get_server_broker_list_url("myhost"),
                         text=get_mock_broker_list_response_func(
                             updated_brokers))

            cli_run()

            self.assertEqual(2, len(req_mock.request_history))

            # Validate auth credentials sent in requests
            expected_creds = "Basic {}".format(base64.b64encode(
                b"myuser:mypass").decode("utf8"))
            for request in req_mock.request_history:
                self.assertEqual(expected_creds,
                                 request.headers["Authorization"])

            # Validate updates to the ca bundle file
            self.assertTrue(os.path.exists(ca_bundle_file))
            ca_bundle_from_file = slurp_file_into_bytes(ca_bundle_file)
            self.assertEqual(updated_ca_bundle.encode("utf8"),
                             ca_bundle_from_file)

            # Validate updates to the config file
            self.assertTrue(os.path.exists(config_file))
            config_from_file = slurp_file_into_bytes(config_file)
            self.assertEqual(expected_config_content, config_from_file)

    def test_updateconfig_with_trusted_ca_cert_and_port(self):
        with _TempDir("updateconfig_ca_port") as temp_dir, \
                patch("sys.argv", command_args(["updateconfig",
                                                temp_dir,
                                                "myhost",
                                                "-t", "58443",
                                                "-u", "myuser",
                                                "-p", "mypass",
                                                "-e", "mytruststore.pem"])), \
                requests_mock.mock(case_sensitive=True) as req_mock:
            ca_bundle_file = os.path.join(temp_dir, "ca-bundle.crt")
            DxlUtils.save_to_file(ca_bundle_file, "old ca")

            config_file = os.path.join(temp_dir, "dxlclient.config")
            DxlUtils.save_to_file(config_file, make_config())

            client_ca_url = get_server_client_ca_url("myhost", 58443)
            broker_list_url = get_server_broker_list_url("myhost", 58443)
            req_mock.get(client_ca_url,
                         text=get_mock_ca_bundle_response_func())
            req_mock.get(broker_list_url,
                         text=get_mock_broker_list_response_func())

            cli_run()

            self.assertEqual(2, len(req_mock.request_history))

            request_urls = []
            for request in req_mock.request_history:
                self.assertEqual("mytruststore.pem", request.verify)
                request_urls.append("{}://{}:{}{}".format(
                    request.scheme,
                    request.hostname,
                    request.port,
                    request.path))

            # If each mock endpoint was hit once, the request should have been
            # made to the right port
            self.assertIn(client_ca_url, request_urls)
            self.assertIn(broker_list_url, request_urls)

    def test_updateconfig_with_prompt_for_server_user_and_password(self):
        responses = {"Enter server username:": "myuser",
                     "Enter server password:": "mypass"}
        def prompt_response(arg):
            return responses[arg]

        with _TempDir("updateconfig_no_server_creds") as temp_dir, \
                patch("sys.argv", command_args(["updateconfig",
                                                temp_dir,
                                                "myhost"])), \
                patch.object(getpass, "getpass",
                             side_effect=prompt_response) as mock_getpass, \
                requests_mock.mock(case_sensitive=True) as req_mock:
            ca_bundle_file = os.path.join(temp_dir, "ca-bundle.crt")
            DxlUtils.save_to_file(ca_bundle_file, "old ca")

            config_file = os.path.join(temp_dir, "dxlclient.config")
            DxlUtils.save_to_file(config_file, make_config())

            client_ca_url = get_server_client_ca_url("myhost")
            broker_list_url = get_server_broker_list_url("myhost")
            req_mock.get(client_ca_url,
                         text=get_mock_ca_bundle_response_func())
            req_mock.get(broker_list_url,
                         text=get_mock_broker_list_response_func())

            cli_run()

            self.assertEqual(2, len(req_mock.request_history))

            # Validate auth credentials sent in requests
            expected_creds = "Basic {}".format(base64.b64encode(
                b"myuser:mypass").decode("utf8"))
            for request in req_mock.request_history:
                self.assertEqual(expected_creds,
                                 request.headers["Authorization"])

            self.assertEqual(2, mock_getpass.call_count)


def slurp_file_into_bytes(filename):
    with open(filename) as handle:
        return handle.read().encode('utf8')


def get_server_provision_url(host, port=8443):
    return "https://{}:{}/remote/{}".format(
        host, port,
        "DxlBrokerMgmt.generateOpenDXLClientProvisioningPackageCmd")


def get_server_client_ca_url(host, port=8443):
    return "https://{}:{}/remote/DxlClientMgmt.createClientCaBundle".format(
        host, port)


def get_server_broker_list_url(host, port=8443):
    return "https://{}:{}/remote/DxlClientMgmt.getBrokerList".format(
        host, port)


def make_broker_lines(brokers=3):
    broker_lines = []
    for i in range(1, brokers+1):
        broker_id = "{{{}}}".format(uuid.UUID(int=i))
        broker_value = ";".join((broker_id,
                                 "888{}".format(i),
                                 "broker{}".format(i),
                                 "10.10.100.{}".format(i)))
        broker_lines.append((broker_id, broker_value))
    return broker_lines


def make_broker_dict(brokers=3):
    return {
        "brokers": [{"guid": "{{{}}}".format(uuid.UUID(int=i)),
                     "hostName": "broker{}".format(i),
                     "ipAddress": "10.10.100.{}".format(i),
                     "port": "888{}".format(i)}
                    for i in range(1, brokers+1)],
        "certVersion": 0,
        "webSocketBrokers": [{"guid": "{{{}}}".format(uuid.UUID(int=i)),
                              "hostName": "broker{}".format(i),
                              "ipAddress": "10.10.100.{}".format(i),
                              "port": "888{}".format(i)}
                             for i in range(1, brokers + 1)],
    }


def make_basic_config(client_prefix="client",
                      ca_bundle_file="ca-bundle.crt",
                      add_comments=False):
    if add_comments:
        config = ["[General]",
                  "#UseWebSockets = False\n",
                  "[Certs]",
                  "# Truststore client uses to validate broker",
                  "BrokerCertChain = {}".format(ca_bundle_file),
                  "# Client's certificate",
                  "CertFile = {}.crt".format(client_prefix),
                  "# Client's private key",
                  "PrivateKey = {}.key".format(client_prefix),
                  "\n# Brokers client could connect to",
                  "[Brokers]",
                 ]
    else:
        config = ["[Certs]",
                  "BrokerCertChain = {}".format(ca_bundle_file),
                  "CertFile = {}.crt".format(client_prefix),
                  "PrivateKey = {}.key".format(client_prefix),
                  "\n[Brokers]"]
    return config


def make_config(basic_config_lines=None, broker_lines=None, add_general=True):
    if not basic_config_lines:
        basic_config_lines = make_basic_config()
    if not broker_lines:
        broker_lines = broker_lines_for_config_file(
            make_broker_lines(2))

    return "\n".join(basic_config_lines +
                     [broker_lines] +
                     [get_web_socket_section(broker_lines)] +
                     (["[General]",
                       "#UseWebSockets = False\n"] if add_general else [])).encode("utf8")


def get_web_socket_section(broker_lines=None):
    if not broker_lines:
        broker_lines = broker_lines_for_config_file(
            make_broker_lines(2))
    return "\n".join(["[BrokersWebSockets]"] + [broker_lines])


def flattened_broker_lines(broker_lines,
                           line_separator,
                           key_value_separator,
                           add_comments=False):
    lines_with_kv_pairs_flattened = []

    for i, broker_line in enumerate(broker_lines):
        if add_comments:
            lines_with_kv_pairs_flattened.append(
                "# This is broker {}".format(i+1))
        lines_with_kv_pairs_flattened.append(
            key_value_separator.join(broker_line))

    return line_separator.join(lines_with_kv_pairs_flattened)


def broker_lines_for_server_response(broker_lines):
    return flattened_broker_lines(broker_lines, "\n", "=")


def broker_lines_for_config_file(broker_lines, add_comments=False):
    return "{}\n".format(flattened_broker_lines(broker_lines,
                                                "\n",
                                                " = ",
                                                add_comments))


def make_fake_ca_bundle(ca_certs=3):
    return "".join([FAKE_CERTIFICATE for _ in range(ca_certs)])


def make_ok_response(message, request):
    output = flattened_query_params(request).get(":output")
    return u"OK:\r\n{}\r\n".format(json.dumps(message)
                                   if output == "json" else message)


def get_mock_provision_response_func(ca_bundle=None,
                                     client_cert=None,
                                     brokers=None):
    if not ca_bundle:
        ca_bundle = make_fake_ca_bundle()
    if not client_cert:
        client_cert = FAKE_CERTIFICATE
    if not brokers:
        brokers = broker_lines_for_server_response(make_broker_lines())

    def mock_provision_response(request, _):
        return make_ok_response(",".join((ca_bundle, client_cert, brokers, brokers)),
                                request)
    return mock_provision_response


def get_mock_ca_bundle_response_func(ca_bundle=None):
    if not ca_bundle:
        ca_bundle = make_fake_ca_bundle()

    def mock_ca_bundle_response(request, _):
        return make_ok_response(ca_bundle, request)
    return mock_ca_bundle_response


def get_mock_broker_list_response_func(brokers=None):
    if not brokers:
        brokers = make_broker_dict()

    def mock_broker_list_response(request, _):
        return make_ok_response(json.dumps(brokers), request)
    return mock_broker_list_response


def flattened_query_params(request):
    query_params = {}
    for key, value in request.qs.items():
        query_params[key] = ",".join(value)
    return query_params
