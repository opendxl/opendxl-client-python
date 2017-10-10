Provisioning Overview
=====================

In order for a client to connect to the DXL fabric, the client must have a
trusted certificate and a ``dxlclient.config`` file with broker information.
This section describes the approaches for provisioning the client configuration
and updating the client configuration to incorporate changes over time.

Creating Certificate Files and Configuration
********************************************

The following approaches are available for creating certificate and
configuration content:

1. To generate certificate and configuration files from the command line -- for
   either an OpenDXL-based or ePO-managed broker -- see the
   :doc:`cliprovisioning` section. Note that with this approach, the
   certificate and key used by the Certificate Authority is managed entirely by
   the server. Note that the provisioning command line tool is only available
   in version 4.0 and later of the Python DXL client.

2. If you are using OpenDXL-based brokers but do not want to use the command
   line interface, you can use the OpenDXL Broker Console to generate and
   download certificate and configuration files. See the
   :doc:`openconsoleprovisioning` section for more information.

3. If your brokers are managed by ePO but you want to manage issuance of client
   certificates from a Certificate Authority outside of ePO, see the steps in
   the :doc:`epoexternalcertissuance` section.

Updating Certificate Files and Configuration
********************************************

After the initial configuration is established for a new client, the
configuration may periodically need to be updated. For example, new brokers may
be connected to the fabric or prior brokers may be removed from the fabric.
Additionally, the server may periodically issue new certificates which clients
should import into their truststore. While this information could be updated
"manually", the :doc:`updatingconfigfromcli` section describes how client
configuration can be updated programmatically via the use of a command line
tool.

Note that the update configuration command line tool is only available in
version 4.0 and later of the Python DXL client.
