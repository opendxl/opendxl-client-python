# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2017 McAfee Inc. - All Rights Reserved.
################################################################################

import traceback
from Queue import Queue
from threading import Thread
import logging

from dxlclient import _BaseObject, _ObjectTracker
from dxlclient._uuid_generator import UuidGenerator

logger = logging.getLogger(__name__)


class ThreadPoolWorker(Thread):
    """
    Thread executing tasks from a given tasks queue.
    """

    def __init__(self, tasks, thread_prefix):
        """
        Constructs a ThreadPoolWorker.
        """
        Thread.__init__(self)

        _ObjectTracker.get_instance().obj_constructed(self)

        self.tasks = tasks
        self.daemon = True
        self.name = thread_prefix + "-" + UuidGenerator.generate_id_as_string()
        self.start()

    def __del__(self):
        _ObjectTracker.get_instance().obj_destructed(self)

    def run(self):
        """
        Runs the worker.
        """
        while True:
            func, args, kargs = self.tasks.get()
            try:
                if func is None:
                    # Exit the thread
                    return
                else:
                    func(*args, **kargs)  # pylint: disable=star-args
            except Exception as ex:  # pylint: disable=broad-except
                logger.error("Error in worker thread: %s", ex.message)
                logger.debug(traceback.format_exc())
            del func
            self.tasks.task_done()


class ThreadPool(_BaseObject):
    """
    Pool of threads consuming tasks from a queue.
    """

    def __init__(self, queue_size, num_threads, thread_prefix):
        """
        Creates a ThreadPool.
        """
        super(ThreadPool, self).__init__()
        self._tasks = Queue(queue_size)
        self._threads = []
        for _ in range(num_threads):
            t = ThreadPoolWorker(self._tasks, thread_prefix)
            self._threads.append(t)

    def __del__(self):
        """destructor"""
        super(ThreadPool, self).__del__()

    def add_task(self, func, *args, **kargs):
        """Add a task to the queue"""
        self._tasks.put((func, args, kargs))

    def wait_completion(self):
        """Wait for completion of all the tasks in the queue"""
        self._tasks.join()

    def shutdown(self):
        """Shuts down the thread pool"""
        logger.info("Shutting down thread pool...")
        self.wait_completion()

        # Add task to stop the thread
        for _ in self._threads:
            self.add_task(None)

        # Wait for threads to exit
        for t in self._threads:
            t.join()

