#> Python 3.5

import collections, uuid, random, time, Queue
import numpy as np

NUM_INIT_NODES = 600
NUM_SEEDERS = 6
DNS_QUERY_SIZE = 40

node  = collections.namedtuple('Node', ['ipV4Addr',
                                        'nonce',
                                        'nodeType',
                                        'triedTable', # List of dicts mapping IP to timestamp
                                        'newTable', # (Each index of list is a bucket)
                                        'incomingCnxs', # List of IP addresses
                                        'outgoingCnxs'])
event = collections.namedtuple('Event', ['srcNode', 'destNode', 'eventType', 'info'])

#> Generate random IPv4 address

randomIP = lambda: '.'.join([str(random.randint(0, 255)) for _ in range(4)])
randomLatency = lambda: random.random() / 2

#> Network Info Helpers

triedRecord = collections.namedtuple('triedRecord', ['timestamp', 'bucket'])
newRecord = collections.namedtuple('newRecord', ['timestamp', 'bucket'])

hardcodedIPs = []
ipToNodes = {}
ipToNonDarkNodes = {}

seederNodes = []
nodes = []
initNodes = []

eventLog = None
globalTime = 0

def mapToTriedBucket(node, ipAddr):
    temp = ipAddr.split('.')
    ipGroup = temp[0] + '.' + temp[1] # /16 group, i.e. first two numbers
    rand = str(node.nonce)
    ival = hash(rand + ipAddr) % 4
    ibkt = hash(rand + ipGroup + str(ival)) % 64
    return ibkt

def addToTried(node, ipAddr, dtMin = 0):
    global globalTime
    bucket = mapToTriedBucket(node, ipAddr)
    if ipAddr in node.triedTable[bucket]:
        # Only update if last message was > dtMin seconds ago.
        if globalTime - node.triedTable[bucket][ipAddr] >= dtMin:
            node.triedTable[bucket][ipAddr] = dtMin
    else:
        if len(node.triedTable[bucket]) == 64:
            # Bitcoin eviction: remove four random addresses, replace oldest with new & put oldest in new table.
            indices = [random.randint(0, 63) for _ in range(4)]
            oldestIP, oldestTimestamp = None, globalTime
            IPs = node.triedTable[bucket].keys()
            for i in indices:
                ip = IPs[i]
                timestamp = node.triedTable[bucket][ip]
                if timestamp < oldestTimestamp:
                    oldestIP, oldestTimestamp = ip, timestamp
            del node.triedTable[bucket][oldestIP] 
            node.triedTable[bucket][ipAddr] = globalTime
            addToNew(ipToNodes[oldVal], ipAddr, oldVal)

            if oldestIP in node.incomingCnxs:
                node.incomingCnxs.remove(oldestIP)
            elif oldestIP in node.outgoingCnxs:
                node.outgoingCnxs.remove(oldestIP)
        else:
            node.triedTable[bucket][ipAddr] = globalTime

def mapToNewBucket(node, ipAddr, peerIP):
    temp = ipAddr.split('.')
    ipGroup = temp[0] + '.' + temp[1]

    temp = peerIP.split('.')
    srcIPGroup = temp[0] + '.' + temp[1] 

    rand = str(node.nonce)
    ival = hash(rand + ipGroup + srcIPGroup) % 32
    ibkt = hash(rand + srcIPGroup + str(ival)) % 256
    return ibkt

# Returns terrible address from given bucket dictionary 
# An address is terrible when it is more than 30 days old 
# or has too many failed connection attempts
def isTerrible(bucket_dict):
    for ip in bucket_dict:
        if globalTime - bucket_dict[ip] == 2592000: # More than 30 days
            return ip
    # If there is no terrible address, return addr via bitcoin eviction
    indices = [random.randint(0, 63) for _ in range(4)]
    oldestIP, oldestTimestamp = None, globalTime
    IPs = bucket_dict.keys()
    for i in indices:
        ip = IPs[i]
        timestamp = bucket_dict[ip]
        if timestamp < oldestTimestamp:
            oldestIP, oldestTimestamp = ip, timestamp
    return oldestIP

def addToNew(node, ipAddr, peerIP):
    global globalTime
    bucket = mapToNewBucket(node, ipAddr, peerIP)
    if len(node.newTable[bucket]) == 64:
        terribleIP = isTerrible(node.newTable[bucket])
        del node.newTable[bucket][terribleIP]
    node.newTable[bucket][ipAddr] = globalTime 

def processEvent(eventEntry):
    global eventLog, globalTime, hardcodedIPs, ipToNodes
    latency = randomLatency()
    #print "Processing " + eventEntry.eventType + " at time " + str(globalTime)
    if eventEntry.eventType == "restart": # Node is restarting
        for ip in eventEntry.srcNode.incomingCnxs:
            eventLog.put((globalTime + latency, event(srcNode = eventEntry.srcNode,
                                                    destNode = ipToNodes[ip],
                                                    eventType = "drop",
                                                    info = "outgoing")))
        
        for ip in eventEntry.srcNode.outgoingCnxs:
            eventLog.put((globalTime + latency, event(srcNode = eventEntry.srcNode,
                                                destNode = ipToNodes[ip],
                                                eventType = "drop",
                                                info = "incoming"))) 
    elif eventEntry.eventType == "drop":
        ipToRemove = eventEntry.srcNode.ipV4Addr
        bucket = mapToTriedBucket(eventEntry.destNode, ipToRemove)
        del eventEntry.destNode.triedTable[bucket][ipToRemove]
        if eventEntry.info == "incoming":
            eventEntry.destNode.incomingCnxs.remove(ipToRemove)
        else:
            eventEntry.destNode.outgoingCnxs.remove(ipToRemove)

        numTriedEntries = sum([len(bucket) for bucket in eventEntry.destNode.triedTable])
        numNewEntries = sum([len(bucket) for bucket in eventEntry.destNode.newTable])
        rho = float(numTriedEntries) / numNewEntries
        omega = len(eventEntry.destNode.outgoingCnxs)
        numRejects = 0
        accepted = False
        PrTried = (rho**0.5) * (9 - omega) 
        PrTried /= (omega + 1) + (rho**0.5) * (9 - omega) 
        table = eventEntry.srcNode.triedTable if random.random() < PrTried else eventEntry.srcNode.newTable
        ip = None
        while not accepted:
            bucketNum = random.randint(0,len(table) - 1)
            bucketPos = random.randint(0,len(table[bucketNum]) - 1)
            ip = table[bucketNum].keys()[bucketPos]
            timestamp = table[bucketNum][ip]
            t = ((globalTime - timestamp) / 600) * 10
            probAccept = min(1, (1.2**numRejects) / float(1+t))
            accepted = random.random() < probAccept
            numRejects += 1
        eventLog.put((globalTime + latency, event(srcNode = eventEntry.destNode,
                                                destNode = ipToNodes[ip],
                                                eventType = "connect",
                                                info = None)))

    elif eventEntry.eventType == "join": # Node requesting to join the network
        seeder = seederNodes[random.randint(0,5)]
        eventLog.put((globalTime + latency, event(srcNode = eventEntry.srcNode, 
                                                  destNode = seeder, 
                                                  eventType = "request connection", 
                                                  info = None)))
    elif eventEntry.eventType == "connect": # Node requesting connection to another node
        if len(eventEntry.destNode.incomingCnxs) <= 117:
            addToTried(eventEntry.srcNode, eventEntry.destNode.ipV4Addr)
            addToTried(eventEntry.destNode, eventEntry.srcNode.ipV4Addr)
            eventEntry.srcNode.outgoingCnxs.append(eventEntry.destNode.ipV4Addr)
            eventEntry.destNode.incomingCnxs.append(eventEntry.srcNode.ipV4Addr)
        else:
            eventLog.put((globalTime + latency, event(srcNode = eventEntry.destNode,
                                                    destNode = eventEntry.srcNode,
                                                    eventType = "connection failure",
                                                    info = None)))
    elif eventEntry.eventType == "connection failure":
        numTriedEntries = sum([len(bucket) for bucket in eventEntry.destNode.triedTable])
        numNewEntries = sum([len(bucket) for bucket in eventEntry.destNode.newTable])
        rho = float(numTriedEntries) / numNewEntries
        omega = len(eventEntry.destNode.outgoingCnxs)
        numRejects = 0
        accepted = False
        PrTried = (rho**0.5) * (9 - omega) 
        PrTried /= (omega + 1) + (rho**0.5) * (9 - omega) 
        table = eventEntry.srcNode.triedTable if random.random() < PrTried else eventEntry.srcNode.newTable
        ip = None
        while not accepted:
            bucketNum = random.randint(0, len(table) - 1)
            bucketPos = random.randint(0, len(table[bucketNum]) - 1)
            ip = table[bucketNum].keys()[bucketPos]
            timestamp = table[bucketNum][ip]
            t = ((globalTime - timestamp) / 600) * 10
            probAccept = min(1, (1.2**numRejects) / float(1+t))
            accepted = random.random() < probAccept
            numRejects += 1
        eventLog.put((globalTime + latency, event(srcNode = eventEntry.destNode,
                                                destNode = ipToNodes[ip],
                                                eventType = "connect",
                                                info = None)))

    elif eventEntry.eventType == "request connection": # Node requesting connection information from seeder
        eventLog.put((globalTime + latency, event(srcNode = eventEntry.destNode, 
                                                  destNode = eventEntry.srcNode, 
                                                  eventType = "connection info", 
                                                  info = hardcodedIPs[:])))
    elif eventEntry.eventType == "connection info": # Node receiving connection information from seeder
        connections = eventEntry.info[:]
        random.shuffle(connections)
        for ip in connections[:8]:
            eventLog.put((globalTime + latency, event(srcNode = eventEntry.destNode, 
                                                      destNode = ipToNodes[ip], 
                                                      eventType = "connect", 
                                                      info = None)))
        for ip in connections[8:]:
            addToNew(eventEntry.destNode, ip, eventEntry.srcNode.ipV4Addr)
    else:
        raise Exception("invalid event type")


def executeSimulation(numNodes = 800, darkNodeProb = 0.5, simulationLength = 86400, timestep = 0.1):
    global eventLog, node, hardcodedIPs, ipToNodes, ipToNonDarkNodes, seederNodes, nodes, initNodes

    realStart = time.time()
    eventLog = Queue.PriorityQueue()

    ipToNodes = {}
    ipToNonDarkNodes = {}

    initNodes = []
    seederNodes = []
    nodes = []

    # Create all of the nodes
    for i in range(numNodes):
        newNode = node(
                ipV4Addr      = randomIP(),
                nonce         = random.randint(0, 65535),
                nodeType      = "dark" if random.random() > darkNodeProb and i > NUM_INIT_NODES + NUM_SEEDERS else "peer",
                triedTable    = [{} for _ in range(64)], # 64 empty buckets
                newTable      = [{} for _ in range(256)],
                incomingCnxs  = [],
                outgoingCnxs  = [])
        while newNode.ipV4Addr in ipToNodes:
            newNode.ipV4Addr = randomIP()

        ipToNodes[newNode.ipV4Addr] = newNode
        if newNode.nodeType != "dark":
            ipToNonDarkNodes[newNode.ipV4Addr] = newNode

        if i < NUM_INIT_NODES: #Initial Nodes
            initNodes.append(newNode)
            restartTime = random.randint(1, simulationLength)
            eventLog.put((restartTime, event(srcNode = newNode, destNode = None, eventType = "join", info = None)))
        elif i < NUM_INIT_NODES + NUM_SEEDERS: # Seeder Nodes
            newNode = newNode._replace(nodeType = "seeder")
            seederNodes.append(newNode)
        else: # All other nodes
            nodes.append(newNode)
            wakeTime = (i - 100) * 0.5 * simulationLength / (numNodes - 100)
            eventLog.put((wakeTime, event(srcNode = newNode, destNode = None, eventType = "join", info = None)))

    # Set up initial nodes for network
    for i in range(len(initNodes)):
        outgoingConnections = [node.ipV4Addr for node in random.sample(initNodes[:i]+initNodes[i+1:], 8)]
        initNodes[i] = initNodes[i]._replace(outgoingCnxs = outgoingConnections)
        for ip in outgoingConnections:
            ipToNodes[ip].incomingCnxs.append(initNodes[i].ipV4Addr)

    hardcodedIPs = [node.ipV4Addr for node in initNodes]

    # Process events in event log
    globalTime = 0
    while not eventLog.empty() and globalTime < simulationLength:
        nextEvent = eventLog.get()
        globalTime = nextEvent[0]
        processEvent(nextEvent[1])

    realEnd = time.time()

    # Simulation done! Return network state & event log.
    print('Simulation complete in %.2f seconds.' % (realEnd - realStart))

    return (nodes, eventLog)


executeSimulation()