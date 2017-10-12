Client Configuration Update via Command Line
============================================

The ``updateconfig`` command line operation can be used to update a previously
provisioned client with the latest information from a management server
(ePO or OpenDXL Broker).

`NOTE: ePO-managed environments must have 4.0 (or newer) versions of
DXL ePO extensions installed.`

The ``updateconfig`` operation performs the following:

* Retrieves the latest CA certificate bundle from the server and stores it
  at the file referenced by the ``BrokerCertChain`` setting in the ``[Certs]``
  section of the ``dxlclient.config`` file.

* Retrieves the latest broker information and updates the ``[Brokers]``
  section of the ``dxlclient.config`` file with that information.

Basic Example
*************

For example::

    python -m dxlclient updateconfig config myserver

For this example, ``config`` is the name of the directory in which the
``dxlclient.config`` file resides and ``myserver`` is the hostname or
IP address of ePO or an OpenDXL Broker.

When prompted, provide credentials for the OpenDXL Broker Management Console
or ePO (the ePO user must be an administrator)::

    Enter server username:
    Enter server password:

If the operation is successful, output similar to the following
should be displayed::

    INFO: Updating certs in config/ca-bundle.crt
    INFO: Updating DXL config file at config/dxlclient.config

To avoid the username and password prompts, supply the appropriate
command line options (``-u`` and ``-p``)::

    python -m dxlclient updateconfig config myserver -u myuser -p mypass

Additional Options
******************

The update operation assumes that the default web server port is 8443,
the default port under which the ePO web interface and OpenDXL Broker Management
Console is hosted.

A custom port can be specified via the ``-t`` option.

For example::

    python -m dxlclient updateconfig config myserver -t 443

If the management server's CA certificate is stored in a local CA truststore
file -- one or more PEM-formatted certificates concatenated together into a
single file -- the update operation can be configured to validate
the management server's certificate against that truststore during TLS session
negotiation by supplying the ``-e`` option.

The name of the truststore file should be supplied along with the option::

    python -m dxlclient updateconfig config myserver -e config/ca-bundle.crt
