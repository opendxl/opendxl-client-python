# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
###############################################################################

"""Helpers for the client cli"""

from __future__ import absolute_import
import argparse
import logging
import sys

from dxlclient._cli._cli_subcommands import \
    GenerateCsrAndPrivateKeySubcommand,\
    ProvisionDxlClientSubcommand,\
    UpdateConfigSubcommand

logger = logging.getLogger(__name__)

_SUBCOMMAND_CLASSES = [GenerateCsrAndPrivateKeySubcommand,
                       ProvisionDxlClientSubcommand,
                       UpdateConfigSubcommand]


def _create_argparser():
    """
    Create the top-level argparser for the cli
    :return: the argparser
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(prog="dxlclient")
    parser.add_argument("-s", "--silent", action="store_true",
                        required=False,
                        help="""show only errors (no info/debug messages)
                            while a command is running""")
    parser.add_argument("-v", "--verbose", action="count",
                        default=0,
                        required=False,
                        help="""Verbose mode. Additional v characters increase
                            the verbosity level, e.g., -vv, -vvv.""")
    return parser


def _add_subcommand_argparsers(parser):
    """
    Append subparsers for each of the cli subcommands to the supplied argparser
    :param argparse.ArgumentParser parser: the base argparser
    """
    subparsers = parser.add_subparsers(title="subcommands")

    # Adding these lines to force argparser to validate the presence of a
    # subcommand in Python 3. See https://bugs.python.org/issue9253#msg186387.
    subparsers.required = True
    subparsers.dest = 'subcommand'

    for subcommand_class in _SUBCOMMAND_CLASSES:
        subcommand = subcommand_class()
        subcommand_parser = subparsers.add_parser(subcommand.name,
                                                  help=subcommand.help,
                                                  parents=subcommand.parents)
        subcommand_parser.set_defaults(func=subcommand.execute)
        subcommand.add_parser_args(subcommand_parser)


def _get_log_level(verbosity_level):
    """
    Translate the supplied numeric verbosity level into a :mod:`logging` level
    :param int verbosity_level: the verbosity level
    :return: An appropriate level from :mod:`logging`, one of
        :const:`logging.ERROR`, :const:`logging.DEBUG`, or
        :const:`logging.INFO`.
    """
    log_level = logging.ERROR
    if verbosity_level >= 2:
        log_level = logging.DEBUG
    elif verbosity_level >= 1:
        log_level = logging.INFO
    return log_level


def _get_log_formatter(verbosity_level):
    """
    Get a log formatter string based on the supplied numeric verbosity level.
    :param int verbosity_level: the verbosity level
    :return: the log formatter string
    :rtype: str
    """
    formatter = "%(levelname)s: %(message)s"
    if verbosity_level >= 3:
        formatter = "%(levelname)s: %(name)s: %(message)s"
    return formatter


def cli_run():
    """
    Main routine for running CLI commands
    """
    parser = _create_argparser()
    _add_subcommand_argparsers(parser)

    input_args = sys.argv[1:]
    if not input_args:
        input_args = ["-h"]
    parsed_args = parser.parse_args(input_args)

    verbosity_level = 0 if parsed_args.silent else parsed_args.verbose+1
    logging.basicConfig(level=_get_log_level(verbosity_level),
                        format=_get_log_formatter(verbosity_level))
    try:
        parsed_args.func(parsed_args)
    except Exception as ex:  # pylint: disable=broad-except
        logger.error("Command failed. Message: %s", ex)
        if verbosity_level >= 2:
            raise
        else:
            sys.exit(1)
