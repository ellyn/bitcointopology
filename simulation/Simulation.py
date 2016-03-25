#> Python 3.5

import collections, uuid, random, time

NUM_INIT_NODES = 600
NUM_SEEDERS = 6

node  = collections.namedtuple('Node', ['ipV4Addr',
                                        'nodeType',
                                        'triedTable',
                                        'triedBuckets',
                                        'newTable',
                                        'incomingCnxs',
                                        'outgoingCnxs',
                                        'hardcodedIPs',
                                        'dnsTable'])
event = collections.namedtuple('Event', ['srcNode', 'destNode', 'eventType'])

#> Generate random IPv4 address

randomIP = lambda: '.'.join([str(random.randint(0, 255)) for _ in range(4)])

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

def executeSimulation(numNodes = 500, darkNodeProb = 0.5, simulationLength = 86400, timestep = 0.1):
    realStart = time.time()

    eventLog = Queue.PriorityQueue()

    ipToNodes = {}
    ipToNonDarkNodes = {}
    initNodes = []
    nodes = []

    for i in range(numNodes):
        newNode = node(
                ipV4Addr      = randomIP(),
                nodeType      = "dark" if random.random() > darkNodeProb and i > NUM_INIT_NODES + NUM_SEEDERS else "peer",
                triedTable    = {},
                triedBuckets  = [[None for _ in range(64)] for _ in range(64)], # 64 empty buckets.
                newTable      = {},
                incomingCnxs  = {}, # TODO limit to 117 (if darknode, 0 connections)
                outgoingCnxs  = {}, # TODO limit to 8
                wakeTime      = 0, # TODO predetermine according to some rate or probability distribution?
                peerMap       = {}, # TODO See above; did you need this as well?
                knownPeersMap = {}, # pairs (knownPeerIPs, salted&hashed knownPeerIPs). Used for ADDR propagation
                eventsPending = {}, # with latency, prevent repeating events
                eventsToDo    = {}, # dictionary (startTime, event)
                incomingEvents = [], # Incoming events (directed to the node)
                dnsTable      = []
            )
        while newNode.ipV4Addr in ipToNodes:
            newNode.ipV4Addr = randomIP()

        ipToNodes[newNode.ipV4Addr] = newNode
        if newNode.nodeType != "dark":
            ipToNonDarkNodes[newNode.ipV4Addr] = newNode

        if i < NUM_INIT_NODES:
            initNodes.append(newNode)
        elif i < NUM_INIT_NODES + NUM_SEEDERS:
            newNode.nodeType = "seeder"
            newNode.hardcodedIPs = [node.ipV4Addr for node in initNodes]
            seederNodes.append(newNodes)
        else:
            nodes.append(newNode)
            eventLog.put(())

    for i in range(len(initNodes)):
        outgoingConnections = [node.ipV4Addr for node in random.randsample(initNodes[:i]+initNodes[i+1:], 8)]
        node.outgoingCnxs = outgoingConnections
        for ip in outgoingConnections:
            ipToNodes[ip].incomingCnxs.append(node)

    globalTime = 0
    while not eventLog.empty() or globalTime < simulationLength:
        globalTime += timestep
        nextEvent = eventLog.get()

    realEnd = time.time()

    # Simulation done! Return network state & event log.
    print('Simulation complete in %.2f seconds.' % (realEnd - realStart))

    return (nodes, eventLog)
