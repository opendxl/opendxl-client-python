External Certificate Authority (CA) Provisioning
================================================

.. _epoexternalcertissuance:

The following steps describe how to provision a client that uses certificates
signed by an externally managed Certificate Authority (CA).

This is in contrast to certificates that are signed by the internal ePO
Certificate Authority (CA).

`NOTE: This step describes the use of an external Certificate Authority (CA)
with an ePO-based DXL fabric. While technically possible with an OpenDXL
Broker, the actual steps are outside the scope of this documentation.`

1. Generate Certificates (CA and Client)

    The :doc:`certcreation` section describes one approach for doing this,
    using ``openssl`` commands to generate a self-signed CA, the client's private
    key, and the client's certificate.

2. Import CA Certificate into ePO

    Follow the steps in the :doc:`epocaimport` section.

3. Export Broker Information

    Follow the steps in the :doc:`epobrokercertsexport` and :doc:`epobrokerlistexport`
    sections to export broker-related configuration information from ePO which is
    utilized in the ``dxlclient.config`` file to connect to a DXL fabric.

Steps
-----

.. toctree::
	:maxdepth: 1

	certcreation
	epocaimport
	epobrokercertsexport
	epobrokerlistexport
