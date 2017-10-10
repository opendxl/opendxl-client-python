ePO Management with External Certificate Issuance
=================================================

If your brokers are managed by ePO but you want to manage issuance of client
certificates from a Certificate Authority outside of ePO, you can follow the
steps below to provision the client's configuration:

1. Generate a client private key and certificate. The :doc:`certcreation`
   section describes one approach for doing this, using ``openssl`` commands to
   generate a self-signed CA, the client's private key, and the client's
   certificate.
2. Follow the steps in the :doc:`epocaimport` section to import the CA
   certificate into ePO.
3. Follow the steps in the :doc:`epobrokercertsexport` and
   :doc:`epobrokerlistexport` sections to export some of the configuration
   data from ePO which is needed to construct the ``dxlclient.config`` file
   that the client uses when connecting to the DXL fabric.

Steps
-----

.. toctree::
	:maxdepth: 1

	certcreation
	epocaimport
	epobrokercertsexport
	epobrokerlistexport
