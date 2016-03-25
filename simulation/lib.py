#> Python 3.5

import collections, uuid, random, time

node  = collections.namedtuple('Node', ['ipV4Addr',
                                        'nodeType',
                                        'triedTable',
                                        'triedBuckets',
                                        'newTable',
                                        'incomingCnxs',
                                        'outgoingCnxs',
                                        'hardcodedIPs',
                                        'wakeTime',
                                        'peerMap', # I realize peerMap is actually accounted for
                                                   # with triedTable and newTable
                                                   # TODO: refactor peerMap -> those tables
                                        'knownPeersMap', # TODO: Did you want this too or was this supposed to be named the above instead?
                                        'eventsPending',
                                        'eventsToDo',
                                        'incomingEvents',
                                        'dnsTable'])
event = collections.namedtuple('Event', ['srcNode', 'destNode', 'eventType'])

#> Generate random IPv4 address

numSeeders = 6
randomIP = lambda: '.'.join([str(random.randint(0, 255)) for _ in range(4)])
seederIPs = [randomIP() for _ in range(numSeeders)]

#> Network Info Helpers

triedRecord = collections.namedtuple('triedRecord', ['timestamp', 'bucket'])

def mapToBucket(ipAddr):
  temp = ipAddr.split('.')
  ipGroup = temp[0] + '.' + temp[1] # /16 group, i.e. first two numbers
  rand = str(random.randint(0, 65535))
  ival = hash(rand + ipAddr) % 4
  ibkt = hash(rand + ipGroup + str(ival)) % 64
  return ibkt

def addToTried(node, ipAddr, dtMin = 0):
  now = time.time()
  if ipAddr in node.triedTable:
    # Only update if last message was > dtMin seconds ago.
    if now - node.triedTable[ipAddr].timestamp >= dtMin:
      node.triedTable[ipAddr].timestamp = dtMin
  else:
    bucket = mapToBucket(ipAddr)
    if all([x is not None for x in node.triedBuckets[bucket]]):
      # Bitcoin eviction: remove four random addresses, replace oldest with new & put oldest in new table.
      indices = [random.randint(0, 63) for _ in range(4)]
      oldInd, oldVal = min([(i, node.triedBuckets[bucket][i]) for i in indices], key = lambda x: x[1].timestamp)  
      node.triedBuckets[bucket] = [x for (i, x) in enumerate(node.triedBuckets[bucket]) if i not in indices]  
      node.triedBuckets[bucket][oldInd] = ipAddr # Store ipAddr in bucket.
      node.triedTable[ipAddr] = triedRecord(timestamp = now, bucket = bucket)
      # TODO: Append oldVal (the evicted IP) to new table.
    else:
      ind = min([i for (i, x) in enumerate(node.triedBuckets[bucket]) if x is None])
      node.triedBuckets[bucket][ind] = ipAddr
      node.triedTable[ipAddr] = triedRecord(timestamp = now, bucket = bucket)

#> React to events! May need additional arguments.

# Given a node and the global timestep, return a list of events.
def react(node, globalTime):
  # TODO implement me completely
  events = []
  
  # fetch DNS
  if(globalTime - node.wakeTime < 1):
    events.append(event(node.ipV4Addr, seederIPs[random.randint(0,numSeeders-1)], 'requestSeeder'))
  # do we need this? was specified in paper (2.1) but maybe we can reduce to above if() only

  '''
  else if(node.wasRestarted):
    if(elapsed >= 11.0 && size(outgoingCnxs) < 2):
        events.append('requestSeeder')
  '''
  
  # connect to peers (try to max out outgoingConnections to 8)
  # TODO: in (8 - _) difference, also subtract size(pendingEvents of type 'connectRequest')
  for peerKey in random.sample(list(peerMap.keys()), 8 - size(outgoingCnxs)):
    events.append(event(node.ipV4Addr, peerMap[peerKey], 'connectRequest'))
  
  # TODO: ADDR propagation (2.1)

  '''
  2.2: Update "tried" table.

  Wasn't quite sure what you meant by "eventsPending" vs "eventsToDo".
  Added "incomingEvents" for e.g. connections but can be switched if something else was intended.
  '''

  for event in node.incomingEvents:
    # An event that should be received when a peer accepts our connect request.
    if event.eventType in 'connectResponse':
      addToTried(node, event.srcNode.ipV4Addr)
    # Events that should be received upon various kinds of network traffic (unsure if we need to simulate all of these or not).
    if event.eventType in ('recvVERSION', 'recvADDR', 'recvINVENTORY', 'recvGETDATA', 'recvPING'):
      addToTried(node, event.srcNode.ipV4Addr, dtMin = 60 * 20)

  return events

def executeSimulation(numNodes = 50, darkNodeProb = 0.5, simulationLength = 86400, timestep = 0.1):

  realStart = time.time()
  
  nodes = [node(
    ipV4Addr      = randomIP(),
    nodeType      = "dark" if random.random() > darkNodeProb else "peer",
    triedTable    = {},
    triedBuckets  = [[None for _ in range(64)] for _ in range(64)], # 64 empty buckets.
    newTable      = {},
    incomingCnxs  = {}, # TODO limit to 117 (if darknode, 0 connections)
    outgoingCnxs  = {}, # TODO limit to 8
    hardcodedIPs  = {}, # TODO ~600 once active peer IPs
    wakeTime      = 1, # TODO predetermine according to some rate or probability distribution?
    peerMap       = {}, # TODO See above; did you need this as well?
    knownPeersMap = {}, # pairs (knownPeerIPs, salted&hashed knownPeerIPs). Used for ADDR propagation
    eventsPending = {}, # with latency, prevent repeating events
    eventsToDo    = {}, # dictionary (startTime, event)
    incomingEvents = [], # Incoming events (directed to the node)
    dnsTable      = []
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
