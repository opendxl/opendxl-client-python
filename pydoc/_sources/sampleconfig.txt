Samples Configuration
=====================

Prior to running any of the examples, make sure you have completed the following:

* Installed the Python SDK (:doc:`installation`)
* Created the Certificate Authority (CA) and Client Certificate Files (:doc:`certcreation`)
* Exported the Broker Certificates (:doc:`epobrokercertsexport`)
* Exported the list of DXL Brokers (:doc:`epobrokerlistexport`)

The final step prior to running the samples is to populate the contents of the ``dxlclient.config``
file that is used by the samples.

The following steps walk through the process of populating this file:

1. Open the ``dxlclient.config`` file located in the ``sample`` sub-directory of the Python DXL SDK.

   The contents should appear as follows:

   .. code-block:: python

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

   .. code-block:: python

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

   .. code-block:: python

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

   .. code-block:: python

       [Certs]
       BrokerCertChain=c:\\certificates\\brokercerts.crt
       CertFile=c:\\certificates\\client.crt
       PrivateKey=c:\\certificates\\client.key

       [Brokers]
       {5d73b77f-8c4b-4ae0-b437-febd12facfd4}={5d73b77f-8c4b-4ae0-b437-febd12facfd4};8883;mybroker.mcafee.com;192.168.1.12
       {24397e4d-645f-4f2f-974f-f98c55bdddf7}={24397e4d-645f-4f2f-974f-f98c55bdddf7};8883;mybroker2.mcafee.com;192.168.1.13

4. At this point you can run the samples included with the Python SDK