Basic Provisioning from the Command Line
========================================

You can use the ``provisionconfig`` command line tool to provision the
configuration data needed for a client to connect to the DXL fabric --
certificates, keys, and broker information. For this tool to be available, you
need to complete the steps in the :doc:`installation` section if you have not
already.

Note that the ``provisionconfig`` tool is only available in version 4.0 and
later of the Python DXL client. The command line tool obtains configuration
data from a management server -- an ePO server or an OpenDXL-based broker. If
you are using an ePO server, version 4.0 of the DXL extensions must also be
installed on the ePO server for use with the command line tool.

Here is an example usage of the tool::

    python -m dxlclient provisionconfig config myserver client1

For this example:

* ``config`` is the name of the directory in which the ``dxlclient.config`` and
  certificate-related artifacts should be stored.
* ``myserver`` is the hostname of a management server. Either a hostname that
  the client can resolve or an IP address can be used.
* ``client1`` is the value for the Common Name (CN) attribute stored in the
  subject of the client's CSR and certificate.

The tool supplies a username and password to the server for authentication.
For ePO or the OpenDXL Broker Console, this would be the same username and
password that you would use to login as an administrator to the web interface.

With the options in the command above, the tool prompts for the username
and password on the command line::

    Enter server username:
    Enter server password:

On success, you should see lines like the following in the tool output::

    INFO: Saving csr file to config/client.csr
    INFO: Saving private key file to config/client.key
    INFO: Saving DXL config file to config/dxlclient.config
    INFO: Saving ca bundle file to config/ca-bundle.crt
    INFO: Saving client certificate file to config/client.crt

To avoid the username and password prompts, you can supply command line
options for them instead, like this::

    python -m dxlclient provisionconfig config myserver client1 -u myuser -p mypass

For more advanced information on the available options for the
``provisionconfig`` tool, see the :doc:`advancedcliprovisioning` section.
