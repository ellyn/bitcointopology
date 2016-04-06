import collections, random, Queue
from constants import *
from node import *

event = collections.namedtuple('Event', ['srcNode', 'destNode', 'eventType', 'info'])

class Network(object):
    def __init__(self, numInitNodes = NUM_INIT_NODES, totalNodes = NUM_NODES, latencyInfo = None, darkNodeProb = 0.2):
        self.eventQueue = Queue.PriorityQueue()
        self.globalTime = 0.0

        self.seederNodes = []
        self.nodes = []
        self.ipToNodes = {}
        self.ipToNonDarkNodes = {}
        self.IPs = []

        self.initializeNodes(numInitNodes)
        self.hardcodedIPs = [node.ipV4Addr for node in initNodes]
        
        self.generateAllNodes(totalNodes - numInitNodes)

    def assignIP():
        ipTaken = True
        while ipTaken:
            newIP = '.'.join([str(random.randint(0, 255)) for _ in range(4)])
            ipTaken = newIP in self.IPs
        self.IPs.append(newIP)
        return newIP

    def getRestartTime():
        pass

    def initializeNodes(self, numInitNodes):
        # Create all of the nodes
        for i in range(numInitNodes):
            newNode = new Node(self.assignIP())
            self.ipToNodes[newNode.ipV4Addr] = newNode
            if newNode.nodeType != DARK:
                self.ipToNonDarkNodes[newNode.ipV4Addr] = newNode
            self.initNodes.append(newNode)
            eventLog.put((self.getRestartTime(), 
                            event(srcNode = newNode,    
                                    destNode = None, 
                                    eventType = JOIN, 
                                    info = None)))

        for i in range(NUM_SEEDERS):
            seederNode = new Node(self.assignIP(), nodeType = SEEDER)
            seederNodes.append(newNode)


    def generateAllNodes(self, numNodes):
        for i in range(numNodes):
            outgoingConnections = [node.ipV4Addr for node in random.sample(self.initNodes[:i]+self.initNodes[i+1:], 8)]
            self.initNodes[i].outgoingCnxs = outgoingConnections
            for ip in outgoingConnections:
                self.ipToNodes[ip].incomingCnxs.append(self.initNodes[i].ipV4Addr)

    def generateLatency():
        pass

    def processNextEvent():
        self.globalTime, nextEvent = eventQueue.get()
        latency = self.generateLatency()
        if nextEvent.