Updating Client Configuration from the Command Line
===================================================

Assuming you have previously created a ``dxlclient.config`` file, you can use
the ``updateconfig`` command line tool to update local client configuration
from the latest configuration available on management server. For this tool to
be available, you need to complete the steps in the :doc:`installation` section
if you have not already. If you used the :doc:`epoexternalcertissuance`
provisioning approach but have not yet created the ``dxlclient.config`` file,
see the :doc:`sampleconfig` section for details on how to create the file.

Note that the ``updateconfig`` tool is only available in version 4.0 and later
of the Python DXL client. The command line tool obtains configuration data from
a management server -- an ePO server or an OpenDXL-based broker. If you are
using an ePO server, version 4.0 of the DXL extensions must also be installed
on the ePO server for use with the command line tool.

The ``updateconfig`` tool does the following:

1) Retrieves the latest CA certificate bundle from the server and stores it
   at the file referenced by the ``BrokerCertChain`` setting in the ``[Certs]``
   section of the ``dxlclient.config`` file.

2) Retrieves the latest broker information and updates the ``[Brokers]``
   section of the ``dxlclient.config`` file with that information.

Basic Example
*************

Here is an example::

    python -m dxlclient updateconfig config myserver

For this example, ``config`` is the name of the directory in which the
``dxlclient.config`` file resides and ``myserver`` is the hostname of an
ePO management server. Either a hostname that the client can resolve or an
IP address can be used.

The tool supplies a username and password to the server for authentication.
For ePO or the OpenDXL Broker Console, this would be the same username and
password that you would use to login as an administrator to the web interface.

With the options in the command above, the tool prompts for the username
and password on the command line::

    Enter server username:
    Enter server password:

On success, you should see lines like the following in the tool output::

    INFO: Updating certs in config/ca-bundle.crt
    INFO: Updating DXL config file at config/dxlclient.config

To avoid the username and password prompts, you can supply command line
options for them instead, like this::

    python -m dxlclient updateconfig config myserver -u myuser -p mypass

Additional Options
******************

The tool assumes that the default webserver port is 8443, the default port
under which the ePO web interface is hosted. You can configure the tool to use
a custom port by using the ``-t`` option. For example::

    python -m dxlclient updateconfig config myserver -t 443

If you have the management server's CA certificate in a local CA truststore
file -- one or more PEM-formatted certificates concatenated together into a
single file -- you can configure the tool to validate the management server's
certificate against that truststore during TLS session negotiation by supplying
the ``-e`` option. The name of the truststore file should be supplied along
with the option, like this::

    python -m dxlclient updateconfig config myserver -e config/ca-bundle.crt
