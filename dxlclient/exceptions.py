# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2017 McAfee Inc. - All Rights Reserved.
################################################################################


class DxlException(Exception):
    """
    A general Data Exchange Layer (DXL) exception
    """


class MalformedBrokerUriException(DxlException):
    """
    An exception that is raised when a URL related to a DXL broker is malformed
    """


class WaitTimeoutException(DxlException):
    """
    Exception that is raised when a wait timeout is exceeded
    """


class BrokerListError(Exception):
    """
    Exception raised when a specified broker list is invalid
    """
    pass


def _raise_wrapped_exception(message, ex):
    """
     Wraps the specified exception as a {@link DxlException} with the specified message.
     If the incoming exception is already a {@link DxlException}, it is simply re-raised
     (no wrapping occurs).

    :param message: The message for the exception
    :param ex: The exception to wrap
    :return: None
    """
    if isinstance(ex, DxlException):
        raise ex
    else:
        raise DxlException(message, ex)
