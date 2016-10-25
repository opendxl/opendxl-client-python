from concurrent.futures import ThreadPoolExecutor


class ThreadRunExecutor(object):

    futures = []

    def __init__(self, run_count):
        self.executor = ThreadPoolExecutor(max_workers=run_count)
        self.run_count = run_count

    def execute(self, command):
        with self.executor as executor:
            for i in range(0, self.run_count):
                self.futures.append(executor.submit(command))
