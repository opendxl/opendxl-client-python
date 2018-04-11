Authorization Overview
================================

DXL topic authorization is used to restrict which clients can "send" and "receive" DXL messages on particular topics.

Examples of using topic authorization include:

* Restricting which clients can provide DXL services.

    When providing a service (McAfee Threat Intelligence Exchange (TIE), etc.) a restriction should be added to ensure that only clients that are providing the service are able to "receive" messages on the service-related topics. Without this protection other clients could masquerade as the service.

* Restricting which clients can invoke DXL services.

    This is accomplished by limiting the clients that can "send" messages on the service-related topics. For example, the clients that can perform McAfee Active Response (MAR) queries are limited using topic authorization (see section :doc:`marsendauth`)

* Restricting which clients can "send" event messages.

    For example, only authorized clients should be able to inform that fabric that a McAfee Threat Intelligence (TIE) reputation has changed by sending a DXL event.

Python-based DXL clients are identified by their certificates. Client-specific certificates and/or Certificate
Authorities (CAs) can be used to limit which clients can send and receive messages on particular topics. A client
certificate can be used to establish a restriction for a single client whereas a certificate authority can be used
to establish a restriction for all clients that were signed by that particular authority.

Please see the :doc:`topicauthgroupcreation` and :doc:`topicauthgrouprestrictions` sections for information on how to
utilize DXL topic authorization.