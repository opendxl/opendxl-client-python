# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
###############################################################################

"""Subcommand classes and helpers for the cli"""

from __future__ import absolute_import
from __future__ import print_function
from abc import ABCMeta, abstractproperty, abstractmethod
import argparse
import getpass
import json
import logging
import os

from dxlclient import Broker, DxlClientConfig
from dxlclient._cli._crypto import X509Name, validate_cert_pem, \
    CsrAndPrivateKeyGenerator
from dxlclient._cli._management_service import ManagementService
from dxlclient import DxlUtils

logger = logging.getLogger(__name__)

_DXL_CONFIG_FILE_NAME = u"dxlclient.config"
_CA_BUNDLE_FILE_NAME = u"ca-bundle.crt"


class _PromptArg(object):
    """
    Parameters that control how the prompt for an argument via standard input
    is done.
    """
    def __init__(self, name, title, confirm=True):
        """
        Constructor parameters:

        :param str name: name of the argument
        :param str title: Text preceding the argument prompt on the cli. For
            example, if "password" is used, the prompt on the cli would be
            "Enter password:".
        :param bool confirm: whether or not to do a confirmation prompt to
            ensure that the user enters the same value twice for the argument
        """
        self._name = name
        self._title = title
        self._confirm = confirm

    @property
    def name(self):
        """
        Name of the argument

        :rtype: str
        """
        return self._name

    @property
    def title(self):
        """
        Text preceding the argument prompt on the cli. For example, if
        "password" is used, the prompt on the cli would be "Enter password:".

        :rtype: str
        """
        return self._title

    @property
    def confirm(self):
        """
        Whether or not to do a confirmation prompt to ensure that the user
        enters the same value twice for the argument

        :rtype: bool
        """
        return self._confirm


def _get_value_from_prompt(title, confirm=False):
    """
    Retrieve a string value from a prompt on standard input. User input
    is not echoed to standard output, making it suitable for password-style
    user input.

    :param str title: Text preceding the argument prompt on the cli. For
        example, if "password" is used, the prompt on the cli would be
        "Enter password:".
    :param bool confirm: whether or not to do a confirmation prompt to
        ensure that the user enters the same value twice for the argument
    :return: value read from the prompt
    :rtype: str
    """
    while True:
        while True:
            value = getpass.getpass("Enter {}:".format(title))
            if not value:
                print("Value cannot be empty. Try again.")
            else:
                break
        confirm_value = getpass.getpass("Confirm {}:".format(title)) \
            if confirm else value
        if value != confirm_value:
            print("Values for {} do not match. Try again.".format(title))
        else:
            break
    return value


def _password_action_prompt(title, confirm=False):
    """
    Return a class which can be used as a custom action to prompt the user
    for password-style input for an :mod:`argparse` argument. The action
    only prompts the user when the value for the associated argument has not
    already been set, e.g., was absent from the command line. User input is
    not echoed to standard output, making it suitable for password input.

    :param str title: Text preceding the argument prompt on the cli. For
        example, if "password" is used, the prompt on the cli would be
        "Enter password:".
    :param bool confirm: whether or not to do a confirmation prompt to
        ensure that the user enters the same value twice for the argument
    :return: A class derived from :class:`argparse.Action` which can be
        supplied as the value for an `action` keyword in a call to
        :func:`argparse.ArgumentParser.add_argument`
    :rtype: type
    """
    class PasswordAction(argparse.Action):
        """
        Custom action class for password argument parsing
        """
        def __call__(self, parser, namespace, values, option_string=None):
            if values is None:
                values = _get_value_from_prompt(title, confirm)
            setattr(namespace, self.dest, values)
    return PasswordAction


def _prompt_required_args(input_args, required_args):
    """
    Prompt the user (via standard input) for the value of any arguments
    which do not exist as attributes on the `input_args` parameter, storing the
    result of each prompt as a new attribute on the `input_args` parameter.

    :param argparse.Namespace input_args: object to check for attributes on
    :param required_args: collection of strings to check against the
        `input_args`
    :type required_args: list(str) or tuple(str) or set(str)
    """
    for required_arg in required_args:
        value = getattr(input_args, required_arg.name)
        if not value:
            value = _get_value_from_prompt(required_arg.title,
                                           required_arg.confirm)
        setattr(input_args, required_arg.name, value)


def _prompt_server_args(args):
    """
    Prompt the user for any arguments required when communicating with a
    server, e.g., user and password, if not set as attributes in `args`. The
    return value for each prompt is stored as an attribute on `args`.

    :param argparse.Namespace args: object with attributes to validate against
        required server info
    """
    _prompt_required_args(args,
                          [_PromptArg("user", "server username",
                                      confirm=False),
                           _PromptArg("password", "server password",
                                      confirm=False)])


def _get_config_argparser():
    """
    Create a :class:`argparse.ArgumentParser` with standard configuration
    options that cli subcommands commonly require.

    :return: the argparser
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("config_dir", metavar="CONFIG_DIR",
                        help="path to the config directory")
    return parser


def _get_crypto_argparser():
    """
    Create a :class:`argparse.ArgumentParser` with standard configuration
    options that crypto-related cli subcommands require, e.g., those which
    create private keys and certificate signing requests.

    :return: the argparser
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-f", "--file-prefix", metavar="PREFIX",
                        default="client",
                        help="""file prefix to use for CSR, key, and cert files.
                            (default: client)""")
    parser.add_argument("-s", "--san", metavar="NAME",
                        required=False, default=None, nargs="*",
                        help="add Subject Alternative Name(s) to the CSR")
    parser.add_argument("-P", "--passphrase", metavar="PASS",
                        action=_password_action_prompt(
                            "private key passphrase",
                            confirm=True),
                        default=None, required=False, nargs="?",
                        help="password for the private key")

    rdn_group = parser.add_argument_group(
        "optional csr subject arguments",
        "key value pairs to append to the CSR's Subject DN")
    rdn_group.add_argument(
        "--country", metavar="COUNTRY",
        default=None,
        help="Country (C) to use in the CSR's Subject DN")
    rdn_group.add_argument(
        "--state-or-province", metavar="STATE",
        default=None,
        help="State or province (ST) to use in the CSR's Subject DN")
    rdn_group.add_argument(
        "--locality", metavar="LOCALITY",
        default=None,
        help="Locality (L) to use in the CSR's Subject DN")
    rdn_group.add_argument(
        "--organization", metavar="ORG",
        default=None,
        help="Organization (O) to use in the CSR's Subject DN")
    rdn_group.add_argument(
        "--organizational-unit", metavar="ORG_UNIT",
        default=None,
        help="Organizational Unit (OU) to use in the CSR's Subject DN")
    rdn_group.add_argument(
        "--email-address", metavar="EMAIL",
        default=None,
        help="e-mail address to use in the CSR's Subject DN")
    return parser


def _get_server_argparser():
    """
    Create a :class:`argparse.ArgumentParser` with standard configuration
    options that cli subcommands which communicate with a server require, e.g.,
    hostname and credential information.

    :return: the argparser
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("host", metavar="HOST_NAME",
                        help="hostname where the management service resides")
    parser.add_argument("-u", "--user", metavar="USERNAME",
                        default=None, required=False,
                        help="user registered at the management service")
    parser.add_argument("-p", "--password", metavar="PASSWORD",
                        default=None, required=False,
                        help="password for the management service user")
    parser.add_argument("-t", "--port", metavar="PORT",
                        required=False, default=8443,
                        help="port where the management service resides")
    parser.add_argument("-e", "--truststore", metavar="TRUSTSTORE_FILE",
                        default=False, required=False,
                        help="""name of file containing one or more CA pems
                            to use in validating the management server""")
    return parser


def get_x509_name_from_cli_args(common_name, args):
    """
    Translate X.509 certificate subject-related attributes from `args` into a
    more strongly-typed :class:`X509Name` object.

    :param str common_name: Common Name (CN) of the subject
    :param argparse.Namespace args: object containing other subject-related
        attributes
    :return: the X.509 name
    :rtype: X509Name
    """
    x509_name = X509Name(common_name)
    x509_name.country_name = args.country
    x509_name.state_or_province_name = args.state_or_province
    x509_name.locality_name = args.locality
    x509_name.organization_name = args.organization
    x509_name.organizational_unit_name = args.organizational_unit
    x509_name.email_address = args.email_address
    return x509_name


def _cert_filename(file_prefix):
    """
    Construct the name of a file for use in storing a certificate.
    :param str file_prefix: base file name for the certificate (without the
        extension)
    :return: certificate file name
    :rtype: str
    """
    return file_prefix + ".crt"


def _csr_filename(file_prefix):
    """
    Construct the name of a file for use in storing a certificate signing
    request.

    :param str file_prefix: base file name for the certificate signing request
        (without the extension)
    :return: certificate signing request file name
    :rtype: str
    """
    return file_prefix + ".csr"


def _private_key_filename(file_prefix):
    """
    Construct the name of a file for use in storing a private key.

    :param str file_prefix: base file name for the private key (without the
        extension)
    :return: private key filename
    :rtype: str
    """
    return file_prefix + ".key"


def generate_csr_and_private_key(common_name, private_key_filename, args):
    """
    Generate a certificate signing request and private key. Files are stored
    to the directory in `args.config_dir`. The certificate signing request
    is stored with a base name from the value for `args.file_prefix`.
    :param str common_name: Common Name (CN) of the subject
    :param str private_key_filename: name of the file in which to store the
        private key
    :param argparse.Namespace args: object with attributes controlling the
        private key and csr to create. Attributes include:
        <X.509 certificate subject-related attributes> (e.g., country,
            email_address>
        san: a list of strings to apply to the new certificate request as
            dns_name entries in a subjectAltName extension
        passphrase: Passphrase to use when encrypting the private key. If None
            is available, the private key is not encrypted.
    :return: the newly created certificate signing request, as a PEM-encoded
        string
    :rtype: str
    """
    x509_name = get_x509_name_from_cli_args(common_name, args)
    generator = CsrAndPrivateKeyGenerator(x509_name,
                                          args.san)
    generator.save_csr_and_private_key(os.path.join(args.config_dir,
                                                    _csr_filename(
                                                        args.file_prefix)),
                                       private_key_filename,
                                       args.passphrase)
    return generator.csr


class Subcommand(ABCMeta('ABC', (object,), {'__slots__': ()})): # compatible metaclass with Python 2 *and* 3
    """
    Abstract base class for cli subcommands
    """
    @abstractproperty
    def help(self):
        """
        Help text to display at the cli for the subcommand
        :rtype: str
        """
        pass

    @abstractproperty
    def name(self):
        """
        Name of the subcommand, used as the argument to identify the subcommand
        on the command line
        :rtype: str
        """
        pass

    @property
    def parents(self):
        """
        List of parent :class:`argparser.ArgumentParser` instances whose
        options should be included for the subcommand.

        :rtype: list(argparse.ArgumentParser) or \
            tuple(argparse.ArgumentParser) or \
            set(argparse.ArgumentParser)
        """
        return ()

    def add_parser_args(self, parser):
        """
        Method invoked with the :class:`argparser.ArgumentParser` added to the
        base parser for this subcommand. In this method call, the subcommand
        can add any extra subcommand-specific arguments to the parser before
        the cli processes them.

        :param argparse.ArgumentParser parser: the subcommand parser
        """
        pass

    @abstractmethod
    def execute(self, args):
        """
        Execution entry point for the subcommand. This method is called when
        the `name` of this subcommand is entered in the cli args
        :param argparse.Namespace args: arguments supplied to the subcommand
        """
        pass


# pylint: disable=no-init
class GenerateCsrAndPrivateKeySubcommand(Subcommand):
    """
    Subcommand for generating a certificate signing request and private key,
    storing each to a file.

    For a list of the attributes that the `execute` method expects
    to be present on its `args` parameter, see the definition of the
    :class:`argparse.ArgumentParser` objects returned by `parents` and
    arguments added in the `add_parser_args` method.
    """
    @property
    def help(self):
        return "generate CSR and private key"

    @property
    def name(self):
        return "generatecsr"

    @property
    def parents(self):
        return _get_config_argparser(), _get_crypto_argparser()

    def add_parser_args(self, parser):
        parser.add_argument(
            "common_name", metavar="COMMON_NAME",
            help="Common Name (CN) to use in the CSR's Subject DN")

    def execute(self, args):
        pk_filename = _private_key_filename(args.file_prefix)
        generate_csr_and_private_key(args.common_name,
                                     os.path.join(args.config_dir,
                                                  pk_filename),
                                     args)


class ProvisionDxlClientSubcommand(Subcommand):  # pylint: disable=no-init
    """
    Subcommand for provisioning a DXL client. This subcommand performs the
    following steps:

    * Either generates a certificate signing request and private key, storing
      each to a file, (the default) or reads the certificate signing request
      from a file (if the "-r" argument is specified).
    * Sends the certificate signing request to a signing endpoint on a
      management server. The HTTP response payload for this request should look
      like the following:

        OK:
        "[ca bundle],[signed client cert],[broker config]"

      Sections of the response include:

      * A line with the text "OK:" if the request was successful, else
        "ERROR <code>:" on failure.
      * A JSON-encoded string with a double-quote character at the beginning
        and end and with the following parts, comma-delimited:

        * [ca bundle] - a concatenation of one or more PEM-encoded CA
          certificates
        * [signed client cert] - a PEM-encoded certificate signed from the
          certificate request
        * [broker config] - zero or more lines, each delimited by a line feed
          character, for each of the brokers known to the management service.
          Each line contains a key and value, delimited by an equal sign. The
          key contains a broker guid. The value contains other metadata for the
          broker, e.g., the broker guid, port, hostname, and ip address. For
          example: "[guid1]=[guid1];8883;broker;10.10.1.1\n[guid2]=[guid2]...".

    * Saves the [ca bundle] and [signed client cert] to separate files.
    * Creates a "dxlclient.config" file with the following sections:

        * A "Certs" section with certificate configuration which refers to the
          locations of the private key, ca bundle, and certificate files.
        * A "Brokers" section with the content of the [broker config] provided
          by the management service.

    For a list of the attributes that the `execute` method expects
    to be present on its `args` parameter, see the definition of the
    :class:`argparse.ArgumentParser` objects returned by `parents` and
    arguments added in the `add_parser_args` method.
    """
    _PROVISION_COMMAND = \
        "DxlBrokerMgmt.generateOpenDXLClientProvisioningPackageCmd"

    @property
    def help(self):
        return "download and provision the DXL client configuration"

    @property
    def name(self):
        return "provisionconfig"

    @property
    def parents(self):
        return (_get_config_argparser(),
                _get_crypto_argparser(),
                _get_server_argparser())

    def add_parser_args(self, parser):
        parser.add_argument("common_or_csrfile_name",
                            metavar="COMMON_OR_CSRFILE_NAME",
                            help="""If "-r" is specified, interpret as the
                                filename for a pre-existing csr. If "-r" is not
                                specified, use as the Common Name (CN) in the
                                Subject DN for a new csr.""")
        parser.add_argument("-r", "--cert-request-file",
                            default=False, action="store_true",
                            help="""Interpret COMMON_OR_CSRFILE_NAME as a
                                filename for an existing csr to be signed. If
                                not specified, a new csr is generated.""")

    @staticmethod
    def _brokers_for_config(broker_lines):
        """
        Convert the supplied broker configuration, a `list` of strings - one
        for each broker - into a list of :class:`Broker` objects. Each string
        in the input list represents a key/value pair, delimited by an equal
        sign. This method uses :meth:`Broker._parse` as a constructor, raising
        an `Exception` any broker configuration lines are syntactically
        invalid.

        :param broker_lines: collection of configuration info for each broker
        :type broker_lines: list(str) or tuple(str) or set(str)
        :return: `list` of broker info
        :rtype: list(Broker)
        """
        brokers = []
        for broker_line in broker_lines:
            try:
                broker_key, broker_value = broker_line.split("=")
            except Exception:
                logger.error("Invalid key value pair for broker entry: %s",
                             broker_line)
                raise
            broker = Broker(host_name="none")
            try:
                broker._parse(broker_value)
            except Exception as ex:
                logger.error("Failed to process broker value: %s. Message: %s",
                             broker_value, ex)
                raise
            if not broker.unique_id:
                raise Exception("No guid for broker: {}".format(broker_value))
            if broker.unique_id != broker_key:
                raise Exception("{}{}{}{}. Broker line: {}".format(
                    "guid for broker key ", broker_key,
                    " did not match guid for broker value: ",
                    broker.unique_id, broker_line))
            brokers.append(broker)
        return brokers

    @staticmethod
    def _process_csr_and_private_key(pk_filename, args):
        """
        Process the certificate signing request and private key for the
        provision operation. If the `cert_request_file` attribute is set for
        `args`, the certificate signing request is read from the file name
        stored in the attribute"s value. If the `cert_request_file` attribute
        is not set, the certificate signing request and private key are
        generated and stored to disk per various attributes in `args`.
        :param str pk_filename: Name of the private key file to create.
        :param argparse.Namespace args: object with attributes used in
            generating the private key and certificate signing request
        :return: string representation of the PEM-encoded certificate signing
            request
        :rtype: str
        """
        if args.cert_request_file:
            cert_request_file = args.common_or_csrfile_name
            if not os.path.isfile(cert_request_file):
                raise Exception(
                    "Unable to locate certificate request file: {}".format(
                        cert_request_file))
            with open(cert_request_file, "r") as file_hnd:
                csr_as_string = file_hnd.read()
        else:
            csr_as_string = generate_csr_and_private_key(
                args.common_or_csrfile_name,
                pk_filename,
                args)
        return csr_as_string

    @staticmethod
    def _save_pem(pem, description, target_file):
        """
        Save the content of the string in the `pem` argument to the file name
        stored in the `target_file` argument.

        :param pem: content of the pem
        :param description: description of the content of the `pem`, used in
            the content of a message for an validation `Exception`, if raised.
        :param target_file: file at which to save the pem
        :raise Exception: if the contents of `pem` does not appear to be a PEM
            wrapping a valid ASN.1-encoded certificate
        """
        validate_cert_pem(pem, "Failed to process PEM for {}".format(
            description))
        logger.info("Saving %s file to %s", description, target_file)
        DxlUtils.save_to_file(target_file, pem)

    def execute(self, args):
        # Prompt the user for any require server credential arguments which
        # were not specified on the command line.
        _prompt_server_args(args)

        pk_filename = _private_key_filename(args.file_prefix)
        csr_as_string = self._process_csr_and_private_key(
            os.path.join(args.config_dir, pk_filename), args)

        svc = ManagementService(args.host, args.port, args.user, args.password,
                                verify=args.truststore)
        data_responses = svc.invoke_command(
            self._PROVISION_COMMAND,
            {"csrString": csr_as_string}).split(",")

        if len(data_responses) < 3:
            raise Exception("{} Expected {}, Received {}. Value: {}".format(
                "Did not receive expected number of response elements.",
                3, len(data_responses), data_responses))

        brokers = self._brokers_for_config(data_responses[2].splitlines())
        config_file = os.path.join(args.config_dir, _DXL_CONFIG_FILE_NAME)
        logger.info("Saving DXL config file to %s", config_file)
        dxlconfig = DxlClientConfig(_CA_BUNDLE_FILE_NAME,
                                    _cert_filename(args.file_prefix),
                                    pk_filename,
                                    brokers)
        dxlconfig.write(config_file)

        self._save_pem(data_responses[0], "ca bundle",
                       os.path.join(args.config_dir,
                                    dxlconfig.broker_ca_bundle))
        self._save_pem(data_responses[1], "client certificate",
                       os.path.join(args.config_dir, dxlconfig.cert_file))


class UpdateConfigSubcommand(Subcommand):  # pylint: disable=no-init
    """
    Subcommand for updating the DXL client configuration in the
    dxlclient.config file, specifically the ca bundle and broker configuration.

    This subcommand performs the following steps:

    * Sends a request to a management server endpoint for the latest ca bundle
      information. The HTTP response payload for this request should look
      like the following:

        OK:
        "[ca bundle]"

      Sections of the response include:

      * A line with the text "OK:" if the request was successful, else
        "ERROR [code]:" on failure.
      * A JSON-encoded string with a double-quote character at the beginning
        and end. The string contains a concatenation of one or more PEM-encoded
        CA certificates.

    * Saves the [ca bundle] to the file at the location specified in the
      "BrokerCertChain" setting in the "Certs" section of the dxlclient.config
      file.

    * Sends a request to a management server endpoint for the latest broker
      configuration. The HTTP response payload for this request should look
      like the following:

        OK:
        "[broker config]"

      Sections of the response include:

      * A line with the text "OK:" if the request was successful, else
        "ERROR [code]:" on failure.
      * A JSON-encoded string with a double-quote character at the beginning
        and end. The string should contain a JSON document which looks similar
        to the following:

        {
            "brokers": [
                {
                    "guid": "{2c5b107c-7f51-11e7-0ebf-0800271cfa58}",
                    "hostName": "broker1",
                    "ipAddress": "10.10.100.100",
                    "port": 8883
                },
                {
                    "guid": "{e90335b2-8dc8-11e7-1bc3-0800270989e4}",
                    "hostName": "broker2",
                    "ipAddress": "10.10.100.101",
                    "port": 8883
                },
                ...
            ],
            "certVersion": 0
        }

    * Saves the [broker config] to the "Brokers" section of the
      dxlclient.config file.

    Updates to the dxlclient.config file attempt to preserve comments in the
    file, when possible. Any comments listed above a broker entry should be
    preserved if the broker continues to be registered. If a broker listed in
    the config file on disk is no longer known to the management server, the
    broker"s config entry and any comments directly above it are removed from
    the config file.

    For a list of the attributes that the `execute` method expects
    to be present on its `args` parameter, see the definition of the
    :class:`argparse.ArgumentParser` objects returned by `parents`.
    """
    _BROKER_CERT_CHAIN_COMMAND = "DxlClientMgmt.createClientCaBundle"
    _BROKER_LIST_COMMAND = "DxlClientMgmt.getBrokerList"

    @property
    def help(self):
        return "update the DXL client configuration"

    @property
    def name(self):
        return "updateconfig"

    @property
    def parents(self):
        return [_get_config_argparser(),
                _get_server_argparser()]

    def _update_broker_cert_chain(self, svc, ca_bundle_file):
        """
        Retrieve the latest ca bundle from the management service and update
        it on disk at the location supplied as the `ca_bundle_file` argument.

        :param dxlclient._cli._management_service.ManagementService svc: the
            management service to query for the new broker cert chain
        :param str ca_bundle_file: file at which to store the latest ca bundle
        """
        cert_chain = svc.invoke_command(self._BROKER_CERT_CHAIN_COMMAND)
        validate_cert_pem(cert_chain, "Failed to process PEM for CA bundle")
        logger.info("Updating certs in %s", ca_bundle_file)
        DxlUtils.save_to_file(ca_bundle_file, cert_chain)

    def _update_broker_config(self, svc, config):
        """
        Retrieve the latest broker configuration from the management service
        and update it in the supplied `config`.

        :param dxlclient._cli._management_service.ManagementService svc: the
            management service to query for the new broker cert chain
        :param dxlclient._cli._provision_config.DxlProvisionConfig config:
            object representing the dxl client configuration
        """
        broker_response = svc.invoke_command(self._BROKER_LIST_COMMAND)
        try:
            brokers = json.loads(broker_response)["brokers"]
            config.brokers = [Broker(broker["hostName"],
                                     broker["guid"],
                                     broker["ipAddress"],
                                     broker["port"]) for broker in brokers]
        except Exception as ex:
            logger.error("Failed to process broker list. Message: %s", ex)
            raise

    def execute(self, args):
        # Prompt the user for any require server credential arguments which
        # were not specified on the command line.
        _prompt_server_args(args)

        config_file = os.path.join(args.config_dir, _DXL_CONFIG_FILE_NAME)

        if not os.path.isfile(config_file):
            raise Exception("Unable to find config file to update: {}".format(
                config_file))

        dxlconfig = DxlClientConfig.create_dxl_config_from_file(config_file)
        svc = ManagementService(args.host, args.port, args.user, args.password,
                                verify=args.truststore)

        self._update_broker_cert_chain(svc, dxlconfig.broker_ca_bundle)
        self._update_broker_config(svc, dxlconfig)

        logger.info("Updating DXL config file at %s", config_file)
        dxlconfig.write(config_file)
