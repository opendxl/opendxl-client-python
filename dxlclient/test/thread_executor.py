"""
Class which executes the specified command a specified number of times, using a
new thread for each execution.
"""

from __future__ import absolute_import
from concurrent.futures import ThreadPoolExecutor

# pylint: disable=missing-docstring


class ThreadRunExecutor(object):

    futures = []

    def __init__(self, run_count):
        self.executor = ThreadPoolExecutor(max_workers=run_count)
        self.run_count = run_count

    def execute(self, command):
        with self.executor as executor:
            for _ in range(0, self.run_count):
                self.futures.append(executor.submit(command))
