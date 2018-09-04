# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c) 2018 McAfee LLC - All Rights Reserved.
###############################################################################

""" DXL utility classes. """

from __future__ import absolute_import
import errno
import os

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
        if not topic:
            return "#"
        splitted = topic.split("/")
        if topic[-1] != "#":
            return "/".join(splitted[:-1]) + "/#"
        if len(topic) == 2:
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

    @staticmethod
    def makedirs(dir_path, mode=0o755):
        """
        Create a directory (or directory tree) per the `dir_path` argument.
        This is basically the same as :func:`os.makedirs` except that if the
        directory already exists when this is called, no exception is raised.
        Also, the default permissions mode is 0o755 instead of what
        :func:`os.makedirs` uses as a default, 0o777.

        :param str dir_path: directory path to create
        :param int mode: permissions mode to use for each directory which is
            created
        """
        if dir_path:
            try:
                os.makedirs(dir_path, mode)
            except OSError as ex:
                if ex.errno != errno.EEXIST:
                    raise

    @staticmethod
    def save_to_file(filename, data, mode=0o644):
        """
        Save a data string to a file. If any directories in the file path do
        not exist, the directories are created (using a permission mode of
        0o755. If the file already exists, its contents are replaced with the
        contents of `data`.

        :param str filename: name of the file to save
        :param data: data to be saved
        :type data: str or bytes
        :param int mode: permissions mode to use for the file
        """
        DxlUtils.makedirs(os.path.dirname(filename))
        with os.fdopen(os.open(filename, os.O_WRONLY | os.O_CREAT, mode),
                       'wb' if isinstance(data, bytes) else 'w') as handle:
            handle.write(data)


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
