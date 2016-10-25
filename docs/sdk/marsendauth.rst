Authorize Client to Perform MAR Search
======================================

By default, McAfee Active Response (MAR) does not allow systems other than the MAR Server to utilize its API over DXL.
In order to allow the McAfee Active Response (MAR) Search Sample to work the "Active Response Server API" authorization
group's send restrictions must be modified to include the Certificate Authority (CA) and/or certificate used by
the client executing the McAfee Active Response (MAR) Search Sample.

Please see :doc:`topicauthoverview` for more information on DXL Topic Authorization.

The following steps will walk through the process of allowing a DXL client to send messages on the
DXL Topic ``/mcafee/mar/service/api/search`` which is associated with the
DXL Topic Authorization Group ``Active Response Server API``::

1. Navigate to **Server Settings** and select the **DXL Topic Authorization** setting on the left navigation bar.

    .. image:: enablemarauth1.png

2. Click the **Edit** button in the lower right corner (as shown in the image above)

    .. image:: enablemarauth2.png

3. Select the check box next to the DXL Topic Authorization Group ``Active Response Server API`` (as shown in the image above)

    .. image:: enablemarauth3.png

4. Click the **Actions** button and select **Restrict Send Certificates** to select certificates allowed to send messages to the topics associated with the ``Active Response Server API`` authorization group (as shown in the image above)

    .. image:: enablemarauth4.png

5. Select the check box next to any certificate to indicate that only DXL Clients with the selected certs or child certs (or tags separately specified) will be allowed to send DXL messages on topics associated with the ``Active Response Server API`` authorization group


    .. image:: enablemarauth5.png

6. Click the **OK** button in the lower right corner (as shown in the image above)


    .. image:: enablemarauth6.png

7. Click the **Save** button in the lower right corner (as shown in the image above)

    .. image:: enablemarauth7.png

The DXL Topic Authorization information will propagate to the DXL brokers. This process can take several minutes
to complete.

