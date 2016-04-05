import collections, random, Queue
from constants import *
from node import *

event = collections.namedtuple('Event', ['srcNode', 'destNode', 'eventType', 'info'])

class Network(object):
    def __init__(self, numInitNodes = INIT_NODES, latencyInfo = None):
        self.globalTime = 0
        self.eventQueue = Queue.PriorityQueue()
        self.ipToNodes = {}

        self.initializeNodes(numInitNodes)

    def initializeNodes(self, numNodes):
        pass

    def addEvent(newEvent):
        pass

    def generateLatency():
        pass

    def processNextEvent():
        self.globalTime, nextEvent = eventQueue.get()
        latency = self.generateLatency()
        if nextEvent.