import sys

if sys.version_info[0] < 3:
    from Queue import Queue
    def iter_dict_items(d):
        return d.iteritems()
    string = basestring
else:
    from queue import Queue
    def iter_dict_items(d):
        return d.items()
    string = str
