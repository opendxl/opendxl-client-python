import logging

from dxlclient import ErrorResponse, Response
from dxlclient.callbacks import RequestCallback
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class TestService(RequestCallback):

    # The Client
    _client = None
    # Whether to return standard responses or errors
    _return_error = False
    # Thread pool
    _executor = None
    # The error code to return
    _error_code = 99
    # The error message to return
    _error_message = "Error"

    def __init__(self, client, thread_count):
        super(TestService, self).__init__()
        self.m_client = client
        self.m_executor = ThreadPoolExecutor(max_workers=thread_count)

    @property
    def return_error(self):
        return self._return_error

    @return_error.setter
    def return_error(self, return_error):
        self._return_error = return_error

    @property
    def error_code(self):
        return self._error_code

    @error_code.setter
    def error_code(self, error_code):
        self._error_code = error_code

    @property
    def error_message(self):
        return self._error_message

    @error_message.setter
    def error_message(self, error_message):
        self._error_message = error_message

    def on_request(self, request):

        if self._return_error:
            response = ErrorResponse(request, error_code=self._error_code, error_message=self._error_message)
        else:
            response = Response(request)

        def run_task():
            try:
                self.m_client.send_response(response)
            except Exception, e:
                logging.info(e.message)
                raise e

        self.m_executor.submit(run_task)

    def close(self):
        self.m_executor.shutdown()
