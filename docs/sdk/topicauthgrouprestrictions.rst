Managing Authorization Group Restrictions
===============================================

Prior to managing certificate-based topic authorization group restrictions, a Certificate Authority (CA) that is being
used to sign client certificates or the certificate for a client must be imported into ePO.

If you have not imported a Certificate Authority (CA) or certificate, please follow the steps outlined in
the :doc:`epocaimport` section. Also if you have not created a topic authorization group, please follow the steps in
the :doc:`topicauthgroupcreation` section.

The following section walks through the steps of limiting which Certificate Authorities (CAs) and/or certificates are
required to send and receive messages for a topic authorization group::


1. Navigate to **Server Settings** and select the **Topic Authorization** setting on the left navigation bar.

    .. image:: addcertbasedauth1.png

#. Click the **Edit** button in the lower right corner (as shown in the image above)

    .. image:: addcertbasedauth2.png

#. Select the check box next to a Topic Authorization Group (as shown in the image above)

    .. image:: addcertbasedauth3.png

#. Click the **Actions** button and select **Restrict Receive Certificates** to select certificates allowed to receive
messages on the topics associated with the selected Topic Authorization Group  (as shown in the image above)

    .. image:: addcertbasedauth4.png

#. Select the check box next to any certificate to indicate that only clients with the selected certs or child certs
will be allowed to receive messages on the topics associated with the selected Topic Authorization Group

    .. image:: addcertbasedauth5.png

#. Click the **OK** button in the lower right corner (as shown in the image above)

    .. image:: addcertbasedauth6.png

#. Select the check box next to a Topic Authorization Group (as shown in the image above)

#. Click the **Actions** button and select **Restrict Send Certificates** to select certificates allowed to send
messages on the topics associated with the selected Topic Authorization Group

    .. image:: addcertbasedauth7.png

#. Select the check box next to any certificate to indicate that only clients with the selected certs or child certs
will be allowed to receive messages on the topics associated with the selected Topic Authorization Group

    .. image:: addcertbasedauth8.png

#. Click the **OK** button in the lower right corner (as shown in the image above)

    .. image:: addcertbasedauth9.png

#. Click the **Save** button in the lower right corner (as shown in the image above)

    .. image:: addcertbasedauth10.png

The Topic Authorization information will propagate to the brokers. This process can take several minutes
to complete.