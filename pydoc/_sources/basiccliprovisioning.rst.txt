Command Line Provisioning (Basic)
=================================

.. _basiccliprovisioning:

The OpenDXL Python Client's command line interface supports the
``provisionconfig`` operation which generates the information necessary for
a client to connect to a DXL fabric (certificates, keys, and broker
information).

As part of the provisioning process, a remote call will be made to a
provisioning server (ePO or OpenDXL Broker) which contains the
Certificate Authority (CA) that will sign the client's certificate.

`NOTE: ePO-managed environments must have 4.0 (or newer) versions of
DXL ePO extensions installed.`

Here is an example usage of ``provisionconfig`` operation::

    python -m dxlclient provisionconfig config myserver client1

The parameters are as follows:

* ``config`` is the directory to contain the results of the provisioning
  operation.
* ``myserver`` is the host name or IP address of the server (ePO or OpenDXL
  Broker) that will be used to provision the client.
* ``client1`` is the value for the Common Name (CN) attribute stored in the
  subject of the client's certificate.

`NOTE:` If a non-standard port (not 8443) is being used for ePO or the
management interface of the OpenDXL Broker, an additional "port" argument
must be specified. For example ``-t 443`` could be specified as part of the
provision operation to connect to the server on port 443.

When prompted, provide credentials for the OpenDXL Broker Management Console
or ePO (the ePO user must be an administrator)::

    Enter server username:
    Enter server password:

On success, output similar to the following should be displayed::

    INFO: Saving csr file to config/client.csr
    INFO: Saving private key file to config/client.key
    INFO: Saving DXL config file to config/dxlclient.config
    INFO: Saving ca bundle file to config/ca-bundle.crt
    INFO: Saving client certificate file to config/client.crt

As an alternative to prompting, the username and password values can be
specified via command line options::

    python -m dxlclient provisionconfig config myserver client1 -u myuser -p mypass

See the :doc:`advancedcliprovisioning` section for advanced
``provisionconfig`` operation options.
