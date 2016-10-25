ePO Certificate Authority (CA) Import
=====================================

Prior to connecting DXL clients to the fabric, a Certificate Authority (CA) that is being used to sign
DXL client certificates must be imported into ePO.

If you have not created the Certificate Authority (CA), please follow the steps outlined in
the :doc:`certcreation` section.

The steps to import the CA certificate into ePO are listed below::

1. Navigate to **Server Settings** and select the **DXL Certificates** setting on the left navigation bar.

    .. image:: serversettings.png

2. Click the **Edit** button in the lower right corner (as shown in the image above)

    .. image:: editdxlcerts.png

3. Click the **Import** button in the **Client Certificates** section (as shown in the image above)

    .. image:: editdxlcerts-selectca.png

4. Select the Certificate (For example, ``ca.crt``) for the Certificate Authority (CA) that was created previously.

   See the :doc:`certcreation` section for information on creating a Certificate Authority (CA)

5. Click the **OK** button in the lower right corner (as shown in the image above)

    .. image:: editdxlcerts-save.png

6. Click the **Save** button in the lower right corner (as shown in the image above)

   The imported Certificate Authority (CA) information will propagate to the DXL brokers. This process can take
   several minutes to complete.

