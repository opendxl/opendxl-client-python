Provisioning Overview
=====================

In order for a client to connect to the DXL fabric it must be provisioned.

A provisioned client includes certificate information required to establish
an authenticated connection to the fabric as well as information regarding
the brokers to connect to.

Provisioning Options
********************

The following options are available for a provisioning a client:

* :ref:`Command Line Interface (CLI) <basiccliprovisioning>`

    The provisioning process is performed via the OpenDXL Python Client's
    command line interface (CLI). A remote call will be made to a
    provisioning server (ePO or OpenDXL Broker) which contains the
    Certificate Authority (CA) that will sign the client's certificate.

    `NOTE: ePO-managed environments must have 4.0 (or newer) versions of
    DXL ePO extensions installed.`

* :ref:`OpenDXL Broker Management Console <openconsoleprovisioning>`

    The OpenDXL Broker Management Console includes a page that will generate
    and download client configuration packages. The OpenDXL Broker's
    Certificate Authority (CA) will be used to sign the certificates.

    `NOTE: This option is not compatible with ePO-managed environments.`

* :ref:`External Certificate Authority (CA) <epoexternalcertissuance>`

    This option allows for the signing of client certificates using an
    external Certificate Authority (CA).

Updating Client Configuration
*****************************

After the initial provisioning of a client, its configuration may
need to be periodically updated. For example, if new brokers are added or
removed from the fabric.

The :doc:`updatingconfigfromcli` section describes how a client's
configuration can be updated via the use of the OpenDXL Python Client's
command line.
