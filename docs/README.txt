DXL Python SDK "3.0.1" Readme
==================================

Welcome to the DXL Python SDK

Please follow the instructions below to get started.


HOW TO PROCEED
----------------------------------

1. Check in "Extensions.zip" to your ePO server. These are specific extensions 
   that provide the support for 3rd party certificates needed for this SDK.

2. Unzip "dxlclient-python-sdk-3.0.1.zip"

3. Open the "README.html" in the directory created from the extraction
   performed in step #2.

Email dxl.sdk.support@intel.com with questions, ideas, and suggestions for
improvement.


KNOWN ISSUES
----------------------------------

Issue: Resources associated with the DxlClient object are not being completely
released when it is destroyed.
Workaround: None

Issue: Response callbacks are not being properly cleaned up when a response is
not received for an outgoing asynchronous request.
Workaround: None

Issue: The DxlClientConfig object does not currently support streaming of the
certificate-related files (requires files to exist of the file system).
Workaround: None

Issue: Some ERROR messages should be changed to WARNINGS (When attempting to
connect to a broker, etc.)
Workaround: None

Issue: Does not work on standard OSX installations (OpenSSL 0.9.8 is installed
by default which does not support TLSv1.2)
Workaround: None

Issue: Does not work on Python 2.6 (TLS support was not introduced until
Python 2.7)
Workaround: None

Issue: Python 3 is not currently supported.
Workaround: None
