# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2017 McAfee Inc. - All Rights Reserved.
################################################################################
from dxlclient import _BaseObject

class DxlUtils(object):
    """
    Utility methods for use by the DXL-related classes
    """

    @staticmethod
    def func_name():
        """
        Returns the current function name
        :return:
        """
        from inspect import currentframe

        return currentframe().f_back.f_code.co_name

    @staticmethod
    def _wildcard_generator(topic):
        """
        Helper method that splits a topic to obtain it's wildcard
        i.e. /foo/bar -> /foo/#
             /foo/bar/ -> /foo/bar/#
             /foo/bar/# -> /foo/#
        :param topic: channel topic.
        :return: wildcarded topic
        """
        if topic is "":
            return "#"
        splitted = topic.split("/")
        if topic[-1] != "#":
            return "/".join(splitted[:-1]) + "/#"
        else:
            if len(topic) is 2:
                return "#"
            return "/".join(splitted[:-2]) + "/#"

    @staticmethod
    def _get_wildcards(topic):
        """
        Helper method that gets a list containing all it's possible wildcards
        :param topic: channel topic
        :return: list containing all channel wildcards
        """
        wildcards = []
        while topic != "#":
            topic = DxlUtils._wildcard_generator(topic)
            wildcards.append(topic)
        return wildcards

    @staticmethod
    def _validate_callback(callback):
        """
        Validates if 'callback' is a valid WildcardCallback

        :param callback: Callback to validate.
        """
        if not issubclass(callback.__class__, WildcardCallback):
            raise ValueError("Type mismatch on callback argument")

    @staticmethod
    def iterate_wildcards(wildcard_callback, topic):
        """
        Iterates the wildcards for the specified topic.
        NOTE: This only supports "#" wildcards (not "+").

        :param wildcard_callback: The callback to invoke for each wildcard
        :param topic: The topic
        :return:
        """

        DxlUtils._validate_callback(wildcard_callback)

        if topic is None:
            return

        topic_wildcards = DxlUtils._get_wildcards(topic)

        for wildcard in topic_wildcards:
            wildcard_callback.on_next_wildcard(wildcard)


class WildcardCallback(_BaseObject):
    """
    Callback that is invoked for each wildcard pattern found
    """

    def on_next_wildcard(self, wildcard):
        """
        Invoked for the next wildcard pattern found

        :param wildcard: The wildcard pattern
        """
        raise NotImplementedError("Must be implemented in a child class.")
