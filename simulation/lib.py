#> Python 3.5

import collections, uuid, random, time

node  = collections.namedtuple('Node', ['ipV4Addr',
                                        'nodeType',
                                        'triedTable',
                                        'newTable',
                                        'incomingCnxs',
                                        'outgoingCnxs',
                                        'hardcodedIPs',
                                        'wakeTime',
                                        'peerMap', # I realize peerMap is actually accounted for
                                                   # with triedTable and newTable
                                                   # TODO: refactor peerMap -> those tables
                                        'eventsPending',
                                        'eventsToDo',
                                        'dnsTable'])
event = collections.namedtuple('Event', ['srcNode', 'destNode', 'eventType'])

#> Generate random IPv4 address

numSeeders = 6
seederIPs = [randomIP() for _ in range(numSeeders)]
randomIP = lambda: '.'.join([str(random.randint(0, 255)) for _ in range(4)])

#> React to events! May need additional arguments.

# Given a node and the global timestep, return a list of events.
def react(node, globalTime):
  # TODO implement me completely
  events = []
  
  # fetch DNS
  if(globalTime - node.wakeTime < 1):
    events.append(event(node.ipV4Addr, seederIPs[random.randint(0,numSeeders-1)], 'requestSeeder')
  # do we need this? was specified in paper (2.1) but maybe we can reduce to above if() only
  '''else if(node.wasRestarted):
    if(elapsed >= 11.0 && size(outgoingCnxs) < 2):
        events.append('requestSeeder')'''
  
  # connect to peers (try to max out outgoingConnections to 8)
  # TODO: in (8 - _) difference, also subtract size(pendingEvents of type 'connectRequest')
  for peerKey in random.sample(list(peerMap.keys()), 8 - size(outgoingCnxs)):
    events.append(event(node.ipV4Addr, peerMap[peerKey], 'connectRequest'))
  
  # TODO: ADDR propagation (2.1)
  
  return events

def executeSimulation(numNodes = 50, darkNodeProb = 0.5, simulationLength = 86400, timestep = 0.1):

  realStart = time.time()
  
  nodes = [node(
    ipV4Addr      = randomIP(),
    nodeType      = "dark" if random.random() > darkNodeProb else "peer",
    triedTable    = {},
    newTable      = {},
    incomingCnxs  = {}, # TODO limit to 117 (if darknode, 0 connections)
    outgoingCnxs  = {}, # TODO limit to 8
    hardcodedIPs  = {}, # TODO ~600 once active peer IPs
    wakeTime      = 1, # TODO predetermine according to some rate or probability distribution?
    knownPeersMap = {}, # pairs (knownPeerIPs, salted&hashed knownPeerIPs). Used for ADDR propagation
    eventsPending = {}, # with latency, prevent repeating events
    eventsToDo    = {} # dictionary (startTime, event)
    ) for _ in range(numNodes)]
    
  seederNodes = [node(
    ipV4Addr   = seederIPs[i],
    nodeType = "seeder",
    dnsTable   = {} # TODO if queried, return 4000 at random
    ) for i in range(numSeeders)]

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
      # Maybe randomize some latency? <- goes in dictionary: node.eventsToDo['<startTime>'] = event
      pass

    eventLog += newEvents # Log these for later statistics, potentially?

  realEnd = time.time()

  # Simulation done! Return network state & event log.
  print('Simulation complete in %.2f seconds.' % (realEnd - realStart))

  return (nodes, eventLog)
