#> Python 3.5

import collections, uuid, random

node  = collections.namedtuple('Node', ['ipV4Addr', 'darkNode', 'triedTable', 'newTable'])
event = collections.namedtuple('Event', ['srcNode', 'destNode', 'eventType'])

#> Generate random IPv4 address

randomIP = lambda: '.'.join([str(random.randint(0, 255)) for _ in range(4)])
