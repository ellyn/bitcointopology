#> Python 3.5

import collections, uuid, random, time

node  = collections.namedtuple('Node', ['ipV4Addr', 'darkNode', 'triedTable', 'newTable'])
event = collections.namedtuple('Event', ['srcNode', 'destNode', 'eventType'])

#> Generate random IPv4 address

randomIP = lambda: '.'.join([str(random.randint(0, 255)) for _ in range(4)])

#> React to events! May need additional arguments.

# Given a node and the global timestep, return a list of events.
def react(node, globalTime):
  # TODO implement me
  return []

def executeSimulation(numNodes = 50, darkNodeProb = 0.5, simulationLength = 86400, timestep = 0.1):

  realStart = time.time()
  
  nodes = [node(
    ipV4Addr   = randomIP(),
    darkNode   = random.random() > darkNodeProb, 
    triedTable = {},
    newTable   = {}
    ) for _ in range(numNodes)]

  eventLog = []

  globalTime = 0
  
  while globalTime < simulationLength:

    globalTime += timestep

    newEvents = []
    for aNode in nodes:
      reactions = react(aNode, globalTime)
      newEvents += reactions
      
    for anEvent in newEvents:
      # TODO handle the event, modifying node states as necessary. May need to include randomized latency.
      # Maybe randomize some latency?
      pass

    eventLog += newEvents # Log these for later statistics, potentially?

  realEnd = time.time()

  # Simulation done! Return network state & event log.
  print('Simulation complete in %.2f seconds.' % (realEnd - realStart))

  return (nodes, eventLog)
