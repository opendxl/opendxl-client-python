Python SDK Installation
=======================

Prerequisites
*************

* DXL Brokers (3.0.1 or later) deployed within an ePO managed environment
* DXL Extensions (3.0.1 or later)
* Python 2.7.8 or higher installed within a Windows or Linux environment (Python 3 is not supported at this time)
* PIP (Included with Python 2.7.9 and later) - PIP is the preferred way to install the Python DXL Client SDK,
  but is not required (``setup.py install`` can be used as an alternative).
* An OpenSSL version used by Python that supports TLSv1.2 (Version 1.0.1 or greater)

  * To check the version of OpenSSL used by Python, open a Python shell::

        python

  * Type the following statements::

        >>> import ssl
        >>> ssl.OPENSSL_VERSION

  * The output should appear similar to the following::

        'OpenSSL 1.0.2a 19 Mar 2015'

  * The version must be 1.0.1 or greater. Unfortunately, even the latest versions of OSX (Mac) still have version
    0.9.8 installed. If you wish to use the Python SDK with OSX, one possible workaround is to use a third
    party package manager (such as `Brew <http://brew.sh/>`_) to install a compatible Python and OpenSSL version.

Python SDK Installation
***********************

Use ``pip`` to automatically install the module:

    .. parsed-literal::

        pip install dxlclient-\ |version|\-py2.7-none-any.whl

Or with:

    .. parsed-literal::

        pip install dxlclient-\ |version|\.zip

As an alternative (without PIP), unpack the dxlclient-\ |version|\.zip (located in the lib folder) and run the setup
script:

    .. code-block:: python

        python setup.py install



