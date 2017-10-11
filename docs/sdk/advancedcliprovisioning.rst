Advanced Provisioning from the Command Line
===========================================

The following subsections have more advanced information on the use of the
``provisionconfig`` tool. For an overview of provisioning from the command
line, refer to the :doc:`basiccliprovisioning` section.

.. _subject-attributes-label:

Including Additional Data in the Certificate Signing Request
************************************************************

Attributes other than the Common Name (CN) may also optionally be provided for
the CSR subject. For example::

    python -m dxlclient provisionconfig config myserver client1 --country US --state-or-province Oregon --locality Hillsboro --organization Engineering --organizational-unit "DXL Team" --email-address dxl@mcafee.com

By default, the CSR does not include any Subject Alternative Names. To include
one or more entries of type ``DNS Name``, you can use the ``-s`` option. For
example::

    python -m dxlclient provisionconfig config myserver client1 -s client1.myorg.com client1.myorg.net

.. _encrypting-private-key-label:

Encrypting the Client's Private Key
***********************************

The private key file which the ``provisionconfig`` command generates can
optionally be encrypted with a passphrase. For example::

    python -m dxlclient provisionconfig config myserver client1 --passphrase

If the passphrase is specified with no trailing option (as above), the tool
prompts for the passphrase to be used::

    Enter private key passphrase:

The passphrase can alternatively be specified as an additional argument
following the ``--passpharse`` argument, in which case no prompt is displayed.
For example::

    python -m dxlclient provisionconfig config myserver client1 --passphrase itsasecret

Note that if the private key is encrypted, the passphrase used to encrypt it
will need to be entered as the client tries to use it to connect to the DXL
fabric later on. Currently, the only way to enter this passphrase is via a
prompt made at connection time::

    Enter PEM pass phrase:

Additional Options
******************

The tool assumes that the default webserver port is 8443, the default port
under which the ePO web interface is hosted. You can configure the tool to use
a custom port by using the ``-t`` option. For example::

    python -m dxlclient provisionconfig config myserver client1 -t 443

The tool stores each of the certificate artifacts -- the private key, CSR,
certificate, etc. -- with a base name of ``client`` by default. To use an
alternative base name for the stored files, use the ``-f`` option. For
example::

    python -m dxlclient provisionconfig config myserver client1 -f theclient

For the command line above, lines similar to the following should appear in the
output::

    INFO: Saving csr file to config/theclient.csr
    INFO: Saving private key file to config/theclient.key
    INFO: Saving DXL config file to config/dxlclient.config
    INFO: Saving ca bundle file to config/ca-bundle.crt
    INFO: Saving client certificate file to config/theclient.crt

If you have the management server's CA certificate in a local CA truststore
file -- one or more PEM-formatted certificates concatenated together into a
single file -- you can configure the tool to validate the management server's
certificate against that truststore during TLS session negotiation by supplying
the ``-e`` option. The name of the truststore file should be supplied along
with the option, like this::

    python -m dxlclient config myserver -e config/ca-bundle.crt

Generating the CSR Separately from Signing the Certificate
**********************************************************

By default, the ``provisionconfig`` command generates a CSR and immediately
sends it a management server to be signed. Certificate generation and signing
could alternatively be performed as separate steps -- for example, to enable a
workflow where the CSR is forwarded to a separate system / process which may
obtain the signed certificate at a later time.

To generate the CSR and private key without sending the CSR on to the server,
the ``generatecsr`` command could be used. For example::

    python -m dxlclient generatecsr config client1

For the command line above, lines similar to the following should appear in the
output::

    INFO: Saving csr file to config/client.csr
    INFO: Saving private key file to config/client.key

Note that the ``generatecsr`` command has options similar to those available
in the ``provisionconfig`` command for including additional subject attributes
and/or subject alternative names in the generated CSR and for encrypting the
private key. See the :ref:`subject-attributes-label` and
:ref:`encrypting-private-key-label` sections for more information.

If the ``provisionconfig`` command includes a ``-r`` option, the
``COMMON_OR_CSRFILE_NAME`` argument is interpreted as being the name of a
CSR file to load from disk rather than the Common Name to insert into a new
CSR file. For example::

    python -m dxlclient provisionconfig config myserver -r config/client.csr

In this case, the command line output shows that the certificate and
configuration-related files received from the server are stored but that no
new private key or CSR file is generated::

    INFO: Saving DXL config file to config/dxlclient.config
    INFO: Saving ca bundle file to config/ca-bundle.crt
    INFO: Saving client certificate file to config/client.crt
