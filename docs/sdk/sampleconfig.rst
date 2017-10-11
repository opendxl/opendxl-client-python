Samples Configuration
=====================

Prior to running any of the examples, you will need to have completed the
following:

* Installed the Python SDK (:doc:`installation`)
* Provisioned a private key, certificates, and configuration for the client (:doc:`provisioningoverview`)

If you are using either the :doc:`basiccliprovisioning` or
:doc:`openconsoleprovisioning` approach for client provisioning, see the
:ref:`cli_or_opendxl_broker_provisioning_config` section below for information
on completing the configuration process.

If you are using the :doc:`epoexternalcertissuance` approach for client
provisioning, see the :ref:`epo_external_cert_provisioning_config` section
below for information on completing the configuration process.

.. _cli_or_opendxl_broker_provisioning_config:

Configuration for Command Line or OpenDXL Broker Console Provisioning
*********************************************************************

To setup the key, certificate, and client configuration from the command-line,
run the following command::

    python -m dxlclient provisionconfig sample <my_server_name_or_ip_address> client1

Substitute the host name or IP address of the management server -- ePO or an
OpenDXL broker -- in place of the ``<my_server_name_or_ip_address>`` parameter.

The tool should prompt for server credentials. Enter credentials for a
valid administrator on the server::

    Enter server username:
    Enter server password:

On success, you should see lines like the following in the tool output::

    INFO: Saving csr file to sample/client.csr
    INFO: Saving private key file to sample/client.key
    INFO: Saving DXL config file to sample/dxlclient.config
    INFO: Saving ca bundle file to sample/ca-bundle.crt
    INFO: Saving client certificate file to sample/client.crt

For more information on the ``provisionconfig`` tool, see the
:doc:`basiccliprovisioning` section.

.. _epo_external_cert_provisioning_config:

Configuration for ePO / External Certificate Provisioning
*********************************************************

The final step to complete after the steps in the
:doc:`epoexternalcertissuance` section is to populate the contents of the
``dxlclient.config`` file that is used by the samples.

The following steps walk through the process of populating this file:

1. Open the ``dxlclient.config`` file located in the ``sample`` sub-directory of the Python DXL SDK.

   The contents should appear as follows:

   .. code-block:: ini

       [Certs]
       BrokerCertChain=<path-to-cabundle>
       CertFile=<path-to-dxlcert>
       PrivateKey=<path-to-dxlprivatekey>

       [Brokers]
       unique_broker_id_1=broker_id_1;broker_port_1;broker_hostname_1;broker_ip_1
       unique_broker_id_2=broker_id_2;broker_port_2;broker_hostname_2;broker_ip_2

2. Update the ``CertFile`` and ``PrivateKey`` values to point to the certificate file (``client.crt``) and
   private key file (``client.key``) that were created during the certificate provisioning steps.

   See the :doc:`certcreation` section for more information on the creation of client key-pairs.

   After completing this step the contents of the configuration file should look similar to:

   .. code-block:: ini

       [Certs]
       BrokerCertChain=<path-to-cabundle>
       CertFile=c:\\certificates\\client.crt
       PrivateKey=c:\\certificates\\client.key

       [Brokers]
       unique_broker_id_1=broker_id_1;broker_port_1;broker_hostname_1;broker_ip_1
       unique_broker_id_2=broker_id_2;broker_port_2;broker_hostname_2;broker_ip_2

3. Update the ``BrokerCertChain`` value to point to the Broker Certificates file (``brokercerts.crt``)
   that was created when exporting the Broker Certificates.

   See the :doc:`epobrokercertsexport` section for more information on exporting Broker Certificates.

   After completing this step the contents of the configuration file should look similar to:

   .. code-block:: ini

       [Certs]
       BrokerCertChain=c:\\certificates\\brokercerts.crt
       CertFile=c:\\certificates\\client.crt
       PrivateKey=c:\\certificates\\client.key

       [Brokers]
       unique_broker_id_1=broker_id_1;broker_port_1;broker_hostname_1;broker_ip_1
       unique_broker_id_2=broker_id_2;broker_port_2;broker_hostname_2;broker_ip_2

3. Update the ``[Brokers]`` section to include the contents of the broker list file (``brokerlist.properties``)
   that was created when exporting the Broker List.

   See the :doc:`epobrokerlistexport` section for more information on exporting the Broker List.

   After completing this step the contents of the configuration file should look similar to:

   .. code-block:: ini

       [Certs]
       BrokerCertChain=c:\\certificates\\brokercerts.crt
       CertFile=c:\\certificates\\client.crt
       PrivateKey=c:\\certificates\\client.key

       [Brokers]
       {5d73b77f-8c4b-4ae0-b437-febd12facfd4}={5d73b77f-8c4b-4ae0-b437-febd12facfd4};8883;mybroker.mcafee.com;192.168.1.12
       {24397e4d-645f-4f2f-974f-f98c55bdddf7}={24397e4d-645f-4f2f-974f-f98c55bdddf7};8883;mybroker2.mcafee.com;192.168.1.13
