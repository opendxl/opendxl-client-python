Integration Types
=================
Interaction with the DXL fabric is comprised of two primary roles; Information consumers and information providers.

Consumers
----------

Consumers receive information over the DXL fabric via its multiple communication models.

**Event subscriber**

    An event-based consumer subscribes to topics and passively receives events from publishers (one-to-many communication mode).

    Common use cases that leverage event subscriber integrations include:

    * Orchestration

        A client listens for a particular set of events. Once an event is received an orchestration work flow is initiated.

        For example, a security product detects that a particular endpoint is sending data to a known "command and control" target and as a reaction sends an event to the DXL fabric. A client listening for the particular event initiates an orchestration work flow that triggers a remediation process utilizing other products available on the fabric.

**Service invoker**

    A client that invokes methods on services registered on the DXL fabric. The client actively requests information from the service (one-to-one communication mode).

    Common use cases that leverage service invocation integrations include:

    * Data Collection

        Security services are invoked over the DXL fabric to query information in real-time (running-processes, etc.) or for forensics-based analysis.

    * Orchestration

        As part of an orchestration work flow various security services are invoked for the purpose of data collection, analytics, and remediation.

Providers
---------

Providers distribute information to the DXL fabric via its multiple communication models.

**Event publisher**

    A client that periodically publishes events to specific topics on the DXL fabric (one-to-many communication mode). These events will be delivered to consumers that are currently subscribed to those topics.

    Common use cases that leverage event publisher integrations include:

    * Threat Events

        Events are sent to the fabric to indicate the presence of a threat. For example, malware is detected on a particular endpoint.

    * Informational Events

        Events are sent to the fabric to announce a particular piece of information. For example, a new vulnerability has been published, a user logged into a system, etc.

**Service providers**

    A client that registers a service with the DXL fabric. A service is comprised of one or more methods that are exposed via corresponding topics. These service methods will be invoked by clients by sending a request message to a topic associated with a service-method. Once received, the service replies by sending a response message over the fabric back to the invoking client (one-to-one communication mode).

    Common service integration models include:

    * Native service

        A service is developed with a native DXL fabric integration. For example McAfee Threat Intelligence Exchange (TIE) natively supports communication with DXL fabrics.

    * Wrapped service

        A DXL service wrapper is created that delegates invocations to an existing service's API/SDK. For example, a security service that exposes a REST-based API can be easily wrapped by a DXL service wrapper to provides its functionality on the DXL fabric.