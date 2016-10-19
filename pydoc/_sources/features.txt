Features
=====================================

Location Unaware
-----------------

Communication between clients on the DXL fabric is based on sending "messages" to a "topic". Clients are unaware
of the location of the other DXL clients they are communicating with (its hostname, IP address, etc.).

For example, if a client wanted to determine the reputation for a file, it could send a request message to the topic
``/mcafee/service/tie/file/reputation``. A service would receive the request and send a response with the appropriate
reputation information. All of this communication occurs without either party knowing the location of the other
(they could be in the same building or on the other side of the world).

Persistent Connection
-----------------

Connections are established from a DXL client to a DXL broker. These connections are persistent and allow for
bi-directional communication. The benefits to this style of connection include:

* Firewall Friendly

    Clients are responsible for establishing the connection to brokers (never from a
    broker to a client). Therefore, we can communicate with clients that were previously unreachable.
    For example, a mobile client can connect to a broker exposed in a demilitarized zone (DMZ). Since
    the communication is bi-directional, we can now communicate with the client from products
    also connected to the fabric (sending an agent wakeup for cloud ePO, etc.).

* Near Real-Time Communication

    Communication on the DXL fabric is extremely efficient because the
    expense of continually establishing connections is eliminated.

Multiple communication models
-----------------

DXL Supports two different models of communication. A service-based model with point-to-point (request/response)
communication and a publish/subscribe event-based model.

* Service-based

    The DXL fabric allows for "services" to be registered and exposed that respond to requests
    sent by invoking clients. This communication is point-to-point (one-to-one), meaning the communication is
    solely between an invoking client and the service that is being invoked. It is important to note that in
    this model the client actively invokes the service by sending it requests.

    For example, the Threat Intelligence Exchange service is exposed via DXL allowing for DXL clients to request
    reputations for files and certificates.

* Event-based

    The DXL fabric also allows for event-based communication. This model is typically referred to as
    "publish/subscribe" wherein clients register interest by subscribing to a particular topic and publishers
    periodically send events to that topic. The event is delivered by the DXL fabric to all of the currently
    subscribed clients for the topic. Therefore, a single event sent can reach multiple clients (one-to-many).
    It is important to note that in this model the client passively receives events when they are sent by a publisher.

    For example, Advanced Threat Defense (ATD) servers send events to the topic ``/mcafee/event/atd/file/report`` when
    they have successfully determined the reputation for a file. Any clients currently subscribed to this topic will
    receive the report (Threat Intelligence Exchange Server and the Enterprise Security Manager currently subscribe
    to this topic).

Secure Communication
---------------------

Communication over the DXL fabric is secured via TLS version 1.2 and PKI mutual authentication.

The fabric also supports topic-level authorization wherein individual topics can be restricted in terms of
which clients can publish messages to and which clients can receive messages on a particular topic.

For example, the DXL clients embedded in the Threat Intelligence Exchange servers are the only ones
authorized to publish reputation change events to the topic ``/mcafee/event/tie/file/repchange``.