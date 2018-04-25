# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
################################################################################

"""
Contains the :class:`UuidGenerator` class, which generates formatted UUIDs,
e.g., for applying unique identifiers to new DXL messages.
"""

from __future__ import absolute_import
import uuid


class UuidGenerator(object):
    """
    Generator used to generate a universally unique identifier (UUID) string that
    is all lowercase and has enclosing brackets (following McAfee Agent format).
    """

    @staticmethod
    def generate_id():
        """
        Generates and returns a UUID

        :return: The generated UUID
        """
        return uuid.uuid4()

    @staticmethod
    def generate_id_as_string():
        """
        Generates and returns a random UUID that is all lowercase and has enclosing brackets

        :return: A UUID string that is all lowercase and has enclosing brackets
        """
        return "{" + str(UuidGenerator.generate_id()).lower() + "}"

    @staticmethod
    def from_string(string):
        """
        Converts the specified UUID string into a UUID instance

        :param string: The UUID string
        :return: The corresponding UUID instance
        """
        return uuid.UUID(string)

    @staticmethod
    def to_string(uid):
        """
        Converts the specified UUID into string that is all lowercase and has enclosing brackets

        :param uid: The UUID
        :return: A UUID string that is all lowercase and has enclosing brackets
        """
        return "{" + str(uid).lower() + "}"

    @staticmethod
    def normalize(string):
        """
        Normalizes the specified UUID string

        :param string: The UUID string
        :return: A UUID string that is all lowercase and has enclosing brackets
        """
        return UuidGenerator.to_string(UuidGenerator.from_string(string))
