import collections, random, Queue
from constants import *
from node import Node

event = collections.namedtuple('Event', ['srcNode', 'destNode', 'eventType', 'info'])

class Network(object):
    def __init__(self, numInitNodes = NUM_INIT_NODES, totalNodes = NUM_NODES, latencyInfo = None, darkNodeProb = 0.2):
        self.eventQueue = Queue.PriorityQueue()
        self.globalTime = 0.0

        self.seederNodes = []
        self.initNodes = []
        self.nodes = []
        self.ipToNodes = {}
        self.ipToNonDarkNodes = {}

        self.IPs = [] # Currently taken IP addresses

        self.initializeNodes(numInitNodes)
        self.hardcodedIPs = [node.ipV4Addr for node in self.initNodes]

        self.generateAllNodes(totalNodes - numInitNodes)

    def assignIP(self):
        ipTaken = True
        while ipTaken:
            newIP = '.'.join([str(random.randint(0, 255)) for _ in range(4)])
            ipTaken = newIP in self.IPs
        self.IPs.append(newIP)
        return newIP

    def getRestartTime(self):
        return random.randint(1, 80000) # Change later

    def initializeNodes(self, numInitNodes):
        # Create initial nodes
        for i in range(numInitNodes):
            newNode = Node(self.assignIP())
            self.ipToNodes[newNode.ipV4Addr] = newNode
            if newNode.nodeType != DARK:
                self.ipToNonDarkNodes[newNode.ipV4Addr] = newNode
            self.initNodes.append(newNode)
            self.eventQueue.put((self.getRestartTime(), 
                            event(srcNode = newNode,    
                                    destNode = None, 
                                    eventType = JOIN, 
                                    info = None)))

        # Create seeder nodes
        for i in range(NUM_SEEDERS):
            seederNode = Node(self.assignIP(), nodeType = SEEDER)
            self.seederNodes.append(seederNode)


    def generateAllNodes(self, numNodes):
        for i in range(numNodes):
            outgoingConnections = [node.ipV4Addr for node in random.sample(self.initNodes[:i]+self.initNodes[i+1:], 8)]
            self.initNodes[i].outgoingCnxs = outgoingConnections
            for ip in outgoingConnections:
                self.ipToNodes[ip].incomingCnxs.append(self.initNodes[i].ipV4Addr)

    def generateLatency(self):
        return random.random() / 2

    def processNextEvent(self):
        self.globalTime, eventEntry = self.eventQueue.get()
        latency = self.generateLatency()

        src = eventEntry.srcNode
        dest = eventEntry.destNode
        if eventEntry.eventType == RESTART: # Node is restarting
            for ip in src.incomingCnxs:
                self.eventQueue.put((self.globalTime + latency, event(srcNode = src,
                                                        destNode = self.ipToNodes[ip],
                                                        eventType = DROP,
                                                        info = "outgoing")))
            
            for ip in eventEntry.srcNode.outgoingCnxs:
                self.eventQueue.put((self.globalTime + latency, event(srcNode = src,
                                                    destNode = self.ipToNodes[ip],
                                                    eventType = DROP,
                                                    info = "incoming"))) 
        elif eventEntry.eventType == DROP:
            ipToRemove = src.ipV4Addr
            bucket = dest.mapToTriedBucket(ipToRemove)
            del dest.triedTable[bucket][ipToRemove]
            if eventEntry.info == "incoming":
                dest.incomingCnxs.remove(ipToRemove)
            else:
                dest.outgoingCnxs.remove(ipToRemove)

            numTriedEntries = sum([len(bucket) for bucket in dest.triedTable])
            numNewEntries = sum([len(bucket) for bucket in dest.newTable])
            rho = float(numTriedEntries) / numNewEntries
            omega = len(dest.outgoingCnxs)
            numRejects = 0
            accepted = False
            PrTried = (rho**0.5) * (9 - omega) 
            PrTried /= (omega + 1) + (rho**0.5) * (9 - omega) 
            table = src.triedTable if random.random() < PrTried else src.newTable
            ip = None
            while not accepted:
                bucketNum = random.randint(0, len(table) - 1)
                bucketPos = random.randint(0, len(table[bucketNum]) - 1)
                ip = table[bucketNum].keys()[bucketPos]
                timestamp = table[bucketNum][ip]
                t = ((self.globalTime - timestamp) / 600) * 10
                probAccept = min(1, (1.2**numRejects) / float(1+t))
                accepted = random.random() < probAccept
                numRejects += 1
            self.eventQueue.put((self.globalTime + latency, event(srcNode = dest,
                                                    destNode = self.ipToNodes[ip],
                                                    eventType = CONNECT,
                                                    info = None)))

        elif eventEntry.eventType == JOIN: # Node requesting to join the network
            seeder = self.seederNodes[random.randint(0, NUM_SEEDERS - 1)]
            self.eventQueue.put((self.globalTime + latency, event(srcNode = src, 
                                                      destNode = seeder, 
                                                      eventType = REQUEST_CONNECTION, 
                                                      info = None)))
        elif eventEntry.eventType == CONNECT: # Node requesting connection to another node
            if len(dest.incomingCnxs) <= MAX_INCOMING:
                src.addToTried(dest.ipV4Addr, self.globalTime)
                dest.addToTried(src.ipV4Addr, self.globalTime)
                src.outgoingCnxs.append(dest.ipV4Addr)
                dest.incomingCnxs.append(src.ipV4Addr)
            else:
                self.eventQueue.put((self.globalTime + latency, event(srcNode = dest,
                                                        destNode = src,
                                                        eventType = CONNECTION_FAILURE,
                                                        info = None)))
        elif eventEntry.eventType == CONNECTION_FAILURE:
            numTriedEntries = sum([len(bucket) for bucket in dest.triedTable])
            numNewEntries = sum([len(bucket) for bucket in dest.newTable])
            rho = float(numTriedEntries) / numNewEntries
            omega = len(dest.outgoingCnxs)
            numRejects = 0
            accepted = False
            PrTried = (rho**0.5) * (9 - omega) 
            PrTried /= (omega + 1) + (rho**0.5) * (9 - omega) 
            table = src.triedTable if random.random() < PrTried else src.newTable
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
            self.eventQueue.put((self.globalTime + latency, event(srcNode = dest,
                                                    destNode = self.ipToNodes[ip],
                                                    eventType = CONNECT,
                                                    info = None)))

        elif eventEntry.eventType == REQUEST_CONNECTION: # Node requesting connection information from seeder
            self.eventQueue.put((self.globalTime + latency, event(srcNode = dest, 
                                                      destNode = src, 
                                                      eventType = CONNECTION_INFO, 
                                                      info = self.hardcodedIPs[:])))
        elif eventEntry.eventType == CONNECTION_INFO: # Node receiving connection information from seeder
            connections = eventEntry.info[:]
            random.shuffle(connections)
            for ip in connections[:8]:
                self.eventQueue.put((self.globalTime + latency, event(srcNode = dest, 
                                                          destNode = self.ipToNodes[ip], 
                                                          eventType = CONNECT, 
                                                          info = None)))
            for ip in connections[8:]:
                dest.addToNew(ip, self.globalTime, src.ipV4Addr)
        else:
            raise Exception("invalid event type")