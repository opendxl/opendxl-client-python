Command Line Provisioning (Advanced)
====================================

This page contain details regarding the advanced usage of the
``provisionconfig`` operation.

Refer to :doc:`basiccliprovisioning` for basic usage details.

.. _subject-attributes-label:

Additional Certificate Signing Request (CSR) Information
********************************************************

Attributes other than the Common Name (CN) may also optionally be provided for
the CSR subject.

For example::

    dxlclient provisionconfig config myserver client1 --country US --state-or-province Oregon --locality Hillsboro --organization Engineering --organizational-unit "DXL Team" --email-address dxl@mcafee.com

By default, the CSR does not include any Subject Alternative Names. To include
one or more entries of type ``DNS Name``, provide the ``-s`` option.

For example::

    dxlclient provisionconfig config myserver client1 -s client1.myorg.com client1.myorg.net

.. _encrypting-private-key-label:

Encrypting the Client's Private Key
***********************************

The private key file which the ``provisionconfig`` operation generates can
optionally be encrypted with a passphrase.

For example::

    dxlclient provisionconfig config myserver client1 --passphrase

If the passphrase is specified with no trailing option (as above), the
provision operation prompts for the passphrase to be used::

    Enter private key passphrase:

The passphrase can alternatively be specified as an additional argument
following the ``--passphrase`` argument, in which case no prompt is displayed.

For example::

    dxlclient provisionconfig config myserver client1 --passphrase itsasecret


`NOTE:` If the private key is encrypted, the passphrase used to encrypt it
must be specified when the client attempts to establish a connection to
the DXL fabric.

The only way to enter this passphrase is via a prompt::

    Enter PEM pass phrase:

Additional Options
******************

The provision operation assumes that the default web server port is 8443,
the default port under which the ePO web interface and OpenDXL Broker Management
Console is hosted.

A custom port can be specified via the ``-t`` option.

For example::

    dxlclient provisionconfig config myserver client1 -t 443

The provision operation stores each of the certificate artifacts (private key, CSR,
certificate, etc.) with a base name of ``client`` by default. To use an
alternative base name for the stored files, use the ``-f`` option.

For example::

    dxlclient provisionconfig config myserver client1 -f theclient

The output of the command above should appear similar to the following::

    INFO: Saving csr file to config/theclient.csr
    INFO: Saving private key file to config/theclient.key
    INFO: Saving DXL config file to config/dxlclient.config
    INFO: Saving ca bundle file to config/ca-bundle.crt
    INFO: Saving client certificate file to config/theclient.crt

If the management server's CA certificate is stored in a local CA truststore
file -- one or more PEM-formatted certificates concatenated together into a
single file -- the provision operation can be configured to validate
the management server's certificate against that truststore during TLS session
negotiation by supplying the ``-e`` option.

The name of the truststore file should be supplied along with the option::

    dxlclient config myserver -e config/ca-bundle.crt

Generating the CSR Separately from Signing the Certificate
**********************************************************

By default, the ``provisionconfig`` command generates a CSR and immediately
sends it to a management server for signing. Certificate generation and signing
could alternatively be performed as separate steps -- for example, to enable a
workflow where the CSR is signed by a certificate authority at a later time.

The ``generatecsr`` operation can be used to generate the CSR and private
key without sending the CSR to the server.

For example::

    dxlclient generatecsr config client1

The output of the command above should appear similar to the following::

    INFO: Saving csr file to config/client.csr
    INFO: Saving private key file to config/client.key

Note that the ``generatecsr`` operation has options similar to those available
in the ``provisionconfig`` operation for including additional subject attributes
and/or subject alternative names in the generated CSR and for encrypting the
private key.

See the :ref:`subject-attributes-label` and :ref:`encrypting-private-key-label`
sections for more information.

If the ``provisionconfig`` operation includes a ``-r`` option, the
``COMMON_OR_CSRFILE_NAME`` argument is interpreted as the name of a
CSR file to load from disk rather than the Common Name to insert into a new
CSR file.

For example::

    dxlclient provisionconfig config myserver -r config/client.csr

In this case, the command line output shows that the certificate and
configuration-related files received from the server are stored but no
new private key or CSR file is generated::

    INFO: Saving DXL config file to config/dxlclient.config
    INFO: Saving ca bundle file to config/ca-bundle.crt
    INFO: Saving client certificate file to config/client.crt
