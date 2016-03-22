#> Python 3.5

import collections, uuid, random

node  = collections.namedtuple('Node', ['ipV4Addr', 'darkNode', 'triedTable', 'newTable'])
event = collections.namedtuple('Event', ['srcNode', 'destNode', 'eventType'])

#> Generate random IPv4 address

randomIP = lambda: '.'.join([str(random.randint(0, 255)) for _ in range(4)])

#> 

def executeSimulation(numNodes = 5000, darkNodeProb = 0.5, simulationLength = 86400, timestep = 0.01):
  
  nodes = [node(
    ipV4Addr   = randomIP(),
    darkNode   = random.random() > darkNodeProb, 
    triedTable = {},
    newTable   = {}
    ) for _ in range(numNodes)]

  globalTime = 0
  
  while globalTime < simulationLength:
    globalTime += timestep

    # Do simulation things...
