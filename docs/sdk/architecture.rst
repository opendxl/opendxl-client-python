Architecture
========

The Data Exchange Layer (DXL) architecture is a publish/subscribe-based middleware that allows DXL clients
to communicate with each over the message bus in near-real time.

Broker
------

Brokers are responsible for routing messages between the clients that are connected to the message bus.
Brokers can be connected to each other ("bridged") to allow for redundancy, scalability, and communication
across different geographical locations.

Client
------

Clients connect to brokers for the purposes of exchanging messages. Communication with brokers is over a
TLS-based connection with bi-directional authentication (PKI).

ePO
---

McAfee ePolicy Orchestrator is used to manage McAfee products, including DXL. ePO maintains the DXL fabric
topology information, authorization rules for the fabric, and provides views for visualizing the fabric's
current state.