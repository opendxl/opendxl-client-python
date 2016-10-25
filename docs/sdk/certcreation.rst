Certificate Files Creation (PKI)
================================

The following section walks through the process to create a Certificate Authority (CA) and a key-pair for a DXL client.

Steps 5 through 7 below should be repeated for each DXL client that is going to connect to the
DXL fabric.

Windows
#######

1. Download and install Open SSL for Windows
  * Download from the following location:

        http://www.slproweb.com/products/Win32OpenSSL.html

    Select the Win32 OpenSSL Light or Win64 OpenSSL Light package, depending on your architecture (32-bit or 64-bit).

  * If a message occurs during setup indicating ``...critical component is missing: Microsoft Visual C++ 2008
    Redistributables``, cancel the setup and download one of the following packages (based on your architecture)

    Visual C++ 2008 Redistributables (x86), available at:

        http://www.microsoft.com/downloads/details.aspx?familyid=9B2DA534-3E03-4391-8A4D-074B9F2BC1BF

    Visual C++ 2008 Redistributables (x64), available at:

        http://www.microsoft.com/downloads/details.aspx?familyid=bd2a6171-e2d6-4230-b809-9a8d7548c1b6

2. Open Command Prompt and set OpenSSL environment variables

  * Open a command prompt **(Start > Run > cmd.exe)**

  * Set the following environment variables (adjust OpenSSL path based on your install location)::

        C:\>set OPENSSL_BIN=c:\OpenSSL-Win32\bin

        C:\>set PATH=%OPENSSL_BIN%;%PATH%

        C:\>set OPENSSL_CONF=%OPENSSL_BIN%\openssl.cfg

    *These environment variables could also be permanently defined in your computer settings.*

  * The following steps must take place in this command prompt.

3. Create and change to directory for output files

  * Create directory::

        c:\>mkdir c:\certificates

  * Change to output directory::

        c:\>cd c:\certificates

4. Create Certificate Authority (CA)

  * Create the certificate authority (CA)::

        c:\certificates>openssl req -new -x509 -days 365 -extensions v3_ca -keyout ca.key -out ca.crt

  * Fill out the required information::

        Generating a 2048 bit RSA private key
        ..............................................................+++
        ..............................................................+++
        writing new private key to 'ca.key'
        Enter PEM pass phrase:
        Verifying - Enter PEM pass phrase:
        -----
        You are about to be asked to enter information that will be incorporated
        into your certificate request.
        What you are about to enter is what is called a Distinguished Name or a DN.
        There are quite a few fields but you can leave some blank
        For some fields there will be a default value,
        If you enter '.', the field will be left blank.
        -----
        Country Name (2 letter code) [AU]:US
        State or Province Name (full name) [Some-State]:Oregon
        Locality Name (eg, city) []:Hillsboro
        Organization Name (eg, company) [Internet Widgits Pty Ltd]:Intel
        Organizational Unit Name (eg, section) []:ISECG-CA
        Common Name (e.g. server FQDN or YOUR name) []:John Doe
        Email Address []:john.doe@intel.com

  * At this point you have created the Certificate Authority's private key ``ca.key`` and certificate
    ``ca.crt``.

    * *Remember* the PEM pass phrase you entered when creating the private key (this is necessary when signing client
      certificates).
    * *Protect* the Certificate Authority private key (``ca.key``).

5. Provision a key-pair for a DXL Client (Python)

  * Generate a Private Key for the client::

        c:\certificates>openssl genrsa -out client.key 2048

  * The following should be displayed::

        Generating RSA private key, 2048 bit long modulus
        .......................+++
        ..................................................+++
        e is 65537 (0x10001)

  * Create a Certificate Signing Request (CSR) for the client::

        c:\certificates>openssl req -out client.csr -key client.key -new

  * Fill out the required information

    The "challenge password" can be blank (the default)

    **NOTE: The "Organizational Unit Name" entered must not be the same as the "Organizational Unit Name" entered in
    Step #4 (Create Certificate Authority)**::

        You are about to be asked to enter information that will be incorporated
        into your certificate request.
        What you are about to enter is what is called a Distinguished Name or a DN.
        There are quite a few fields but you can leave some blank
        For some fields there will be a default value,
        If you enter '.', the field will be left blank.
        -----
        Country Name (2 letter code) [AU]:US
        State or Province Name (full name) [Some-State]:Oregon
        Locality Name (eg, city) []:Hillsboro
        Organization Name (eg, company) [Internet Widgits Pty Ltd]:Intel
        Organizational Unit Name (eg, section) []:ISECG-Client
        Common Name (e.g. server FQDN or YOUR name) []:John Doe
        Email Address []:john.doe@intel.com

        Please enter the following 'extra' attributes
        to be sent with your certificate request
        A challenge password []:
        An optional company name []:

6. Sign the Certificate Signing Request (CSR)

  * Have the Certificate Authority (CA) sign the signing request (CSR)::

        c:\certificates>openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days 365

  * When prompted, enter the CA PEM pass phrase from Step #4, above. You should see output similar to the following::

        Signature ok
        subject=/C=US/ST=Oregon/L=Hillsboro/O=Intel/OU=ISECG-Client/CN=John Doe/emailAddress=john.doe@intel.com
        Getting CA Private Key
        Enter pass phrase for ca.key:

  * At this point you will have a certificate ``client.crt`` and an associated private key ``client.key`` for
    use with a DXL client.

  * These files are specified as ``cert_file`` and ``private_key`` parameters when constructing a
    :class:`dxlclient.client_config.DxlClientConfig` instance.

    These files can also be specified via a configuration file used to instantiate a
    :class:`dxlclient.client_config.DxlClientConfig` instance.

    See the :func:`dxlclient.client_config.DxlClientConfig.create_dxl_config_from_file` method for more information.

7. Validate Certificate (Optional)

  * The following command can be used to ensure the client certificate is valid for the certificate authority::

        c:\certificates>openssl verify -verbose -CAfile ca.crt client.crt

  * If the certificate is valid, you should see the following output::

        client.crt: OK

Linux
#####

The steps for Linux-based platforms are very similar to those listed for Windows above.

Installation of OpenSSL for the various Linux platforms is outside the scope of this document.
