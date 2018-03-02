import sys

try:
    from queue import Queue
except ImportError:
    from Queue import Queue

if sys.version_info[0] > 2:
    def iter_dict_items(d):
        return d.items()
    string = str
else:
    def iter_dict_items(d):
        return d.iteritems()
    string = basestring
