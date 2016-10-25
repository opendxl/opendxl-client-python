ePO Broker Certificates Export
==============================

The certificate information for DXL Brokers must be available to DXL clients attempting to connect
to the fabric. This certificate information allows clients to ensure the Brokers being connected to are valid
(via mutual authentication).

The following steps walk through the process to export the DXL Broker certificate information::

1. Navigate to **Server Settings** and select the **DXL Certificates** setting on the left navigation bar.

    .. image:: serversettings-certs.png

2. Click the **Edit** button in the lower right corner (as shown in the image above)

    .. image:: editdxlcerts-save.png

3. Click the **Export All** button in the **Broker Certificates** section (as shown in the image above)

4. The exported file, ``brokercerts.crt``, will be saved locally.

   This file is specified as the ``broker_ca_bundle`` parameter when constructing a
   :class:`dxlclient.client_config.DxlClientConfig` instance.

   This file can also be specified via a configuration file used to instantiate a
   :class:`dxlclient.client_config.DxlClientConfig` instance.

   See the :func:`dxlclient.client_config.DxlClientConfig.create_dxl_config_from_file` method for more information.


