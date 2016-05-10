import collections, itertools, Queue
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import math
import numpy as np
from constants import *
from node import Node

event = collections.namedtuple('Event', ['srcNode', 'destNode', 'eventType', 'info'])

class Network(object):
    def __init__(self, numInitNodes = NUM_INIT_NODES, totalNodes = NUM_NODES, 
                        latencyInfo = None, darkNodeProb = 0.9):
        self.eventQueue = Queue.PriorityQueue()
        self.globalTime = 0.0
        self.darkNodeProb = darkNodeProb

        self.seederNodes = []
        self.initNodes = []
        self.nodes = []
        self.ipToNodes = {}
        self.ipToNonDarkNodes = {}

        self.IPs = [] # Currently taken IP addresses by nodes in network
        self.IPs.append(HARDCODED_IP_SOURCE)

        self.lastSeederCrawlTime = 0.0

        self.initializeNodes(numInitNodes)
        self.hardcodedIPs = [node.ipV4Addr for node in self.initNodes]

        self.generateAllNodes(totalNodes - numInitNodes)

        self.eventLog = []

    def assignIP(self):
        ipTaken = True
        while ipTaken:
            newIP = '.'.join([str(random.randint(0, 255)) for _ in range(4)])
            ipTaken = newIP in self.IPs
        self.IPs.append(newIP)
        return newIP

    # Based on "Deanonymisation of Clients in Bitcoin P2P Network"
    # Multipled by 3600 to convert hours to seconds
    def getRestartTime(self): 
        return (W_LAMBDA * np.random.weibull(W_K) * 3600) + self.globalTime

    def initializeNodes(self, numInitNodes):
        # Create initial nodes
        for i in range(numInitNodes):
            newNode = Node(self.assignIP())
            newNode.isOnline = True
            self.ipToNodes[newNode.ipV4Addr] = newNode
            self.ipToNonDarkNodes[newNode.ipV4Addr] = newNode
            self.initNodes.append(newNode)
            self.nodes.append(newNode)
            self.eventQueue.put((self.getRestartTime(), event(srcNode = newNode,    
                                                              destNode = None, 
                                                              eventType = RESTART, 
                                                              info = None)))

            # place event to trigger sending ADDR messages
            self.eventQueue.put((0, event(srcNode = None,    
                                          destNode = newNode, 
                                          eventType = NEW_DAY, 
                                          info = None)))

        # Create seeder nodes
        for i in range(NUM_SEEDERS):
            seederNode = Node(self.assignIP(), nodeType = SEEDER)
            seederNode.isOnline = True
            self.ipToNodes[seederNode.ipV4Addr] = seederNode
            self.seederNodes.append(seederNode)

        # Setup connections for initial nodes
        for i in range(numInitNodes):
            connections = self.initNodes[:i] + self.initNodes[i+1:]
            outgoingCnxs = [n.ipV4Addr for n in random.sample(connections, MAX_OUTGOING)]
            self.initNodes[i].outgoingCnxs = outgoingCnxs
            for ip in outgoingCnxs:
                self.ipToNodes[ip].addToIncomingCnxs(self.initNodes[i].ipV4Addr)

        self.simulateSeederCrawl()

    def getWakeTime(self, node):
        lamd = 1 / float(MEAN_START_TIME)
        return random.expovariate(lamd) + self.globalTime

    def generateAllNodes(self, numNodes):
        for i in range(numNodes):
            nType = DARK if random.random() <= self.darkNodeProb else PEER
            newNode = Node(self.assignIP(), nodeType=nType)
            self.nodes.append(newNode)
            self.ipToNodes[newNode.ipV4Addr] = newNode
            if newNode.nodeType != DARK:
                self.ipToNonDarkNodes[newNode.ipV4Addr] = newNode

            wakeTime = self.getWakeTime(newNode)
            self.eventQueue.put((wakeTime, event(srcNode = newNode, 
                                                 destNode = None, 
                                                 eventType = JOIN, 
                                                 info = None)))
            
            # place events to trigger sending ADDR messages
            firstDayAfterWake = (wakeTime / ONE_DAY) + 1
            firstDayInSec = firstDayAfterWake * ONE_DAY
            self.eventQueue.put((firstDayInSec, event(srcNode = None,    
                                                      destNode = newNode, 
                                                      eventType = NEW_DAY, 
                                                      info = None)))

    def generateLatency(self):
        return random.random() / 2 # Change later

    def addCxns(self, node, scheduledTime):
        numTriedEntries = sum([len(bucket) for bucket in node.triedTable])
        numNewEntries = sum([len(bucket) for bucket in node.newTable])

        rho = float(numTriedEntries) / numNewEntries
        omega = len(node.outgoingCnxs)
        numRejects = 0
        accepted = False

        PrTried = (rho**0.5) * (9 - omega) 
        PrTried /= (omega + 1) + (rho**0.5) * (9 - omega) 

        table = node.triedTable if random.random() < PrTried else node.newTable
        ip = None
        if len(node.outgoingCnxs) < MAX_OUTGOING:
          while not accepted:
              bucketNum = random.randint(0, len(table) - 1)
              if len(table[bucketNum]) > 0:
                  bucketPos = random.randint(0, len(table[bucketNum]) - 1)
                  ip = table[bucketNum].keys()[bucketPos]
                  timestamp = table[bucketNum][ip]
                  t = ((self.globalTime - timestamp) / 600) * 10
                  probAccept = min(1, ((1.2)**numRejects) / float(1 + t))
                  accepted = random.random() < probAccept
                  # accepted = accepted and self.ipToNodes[ip].isOnline
                  # NOTE cut - node shouldn't know this
                  numRejects += 1

          self.eventQueue.put((scheduledTime, event(srcNode = node, 
                                                    destNode = self.ipToNodes[ip],
                                                    eventType = CONNECT, 
                                                    info = None)))

    def simulateSeederCrawl(self):
        # Collect IP addresses of all reachable nodes
        network = []
        for ip in self.ipToNonDarkNodes:
            if self.ipToNodes[ip].incomingCnxs > []:
                network.append(ip)

        for seeder in self.seederNodes:
            seeder.updateNetworkInfo(network)
        self.lastSeederCrawlTime = self.globalTime

    # Return # active nodes in network
    def numNodes(self, val_fxn = lambda _: True):
        network = []
        for ip in self.ipToNonDarkNodes:
            if self.ipToNodes[ip].incomingCnxs > []:
                network.append(ip)
        return len(network)

    def processNextEvent(self):
        self.globalTime, eventEntry = self.eventQueue.get()
        self.eventLog.append(eventEntry.eventType)

        if self.lastSeederCrawlTime - self.globalTime >= TIME_BETWEEN_CRAWLS:
            self.simulateSeederCrawl()

        latency = self.generateLatency()
        scheduledTime = self.globalTime + latency

        src = eventEntry.srcNode
        dest = eventEntry.destNode

        # RESTART: A node is restarting. Notifies its connections of its drop.
        #
        # src = node that is restarting
        if eventEntry.eventType == RESTART:
            for ip in src.incomingCnxs:
                self.eventQueue.put((scheduledTime, event(srcNode = src, 
                                                          destNode = self.ipToNodes[ip], 
                                                          eventType = DROP, 
                                                          info = "outgoing")))
            for ip in eventEntry.srcNode.outgoingCnxs:
                self.eventQueue.put((scheduledTime, event(srcNode = src, 
                                                          destNode = self.ipToNodes[ip],
                                                          eventType = DROP, 
                                                          info = "incoming")))
            src.incomingCnxs = []
            src.outgoingCnxs = []
            src.isOnline = False
            self.eventQueue.put((scheduledTime + latency, event(srcNode = src,
                                                                destNode = None,
                                                                eventType = REJOIN,
                                                                info = None)))

        # REJOIN: A node rejoins the network after restarting and tries to make 8 connections,
        #          similarly to how it would if all of its connections had dropped. 
        elif eventEntry.eventType == REJOIN:
            src.isOnline = True
            while src.outgoingCnxs <= MAX_OUTGOING:
                self.addCxns(src, scheduledTime)
            self.eventQueue.put((self.getRestartTime(),event(srcNode = src,
                                                             destNode = None,
                                                             eventType = RESTART,
                                                             info = None)))
            # in 11 seconds, potentially request seeder via AFTER_REJOIN_MAYBE_REQUEST_SEEDER event
            scheduledTime += 11
            self.eventQueue.put((scheduledTime, event(srcNode = src,
                                                      destNode = None,
                                                      eventType = AFTER_REJOIN_MAYBE_REQUEST_SEEDER,
                                                      info = None)))

        # DROP: A node is notified that one of its connections was dropped 
        #        and updates its list of connections accordingly.
        #
        # src = node that was dropped
        # dest = node that was notified to update its connections from the drop
        # info = "incoming" if src was in dest's incoming connections, 
        #           else "outgoing"
        elif eventEntry.eventType == DROP:
            dest.removeFromConnections(src.ipV4Addr)
            self.addCxns(dest, scheduledTime)

        # JOIN: A node is requesting to join the network. 
        #        Randomly chooses a seeder to contact for connection information.
        #        Additionally schedules a time for the node to restart
        #
        # src = node that is requesting to join
        elif eventEntry.eventType == JOIN:
            src.isOnline = True
            seeder = self.seederNodes[random.randint(0, NUM_SEEDERS - 1)]
            self.eventQueue.put((scheduledTime, event(srcNode = src, 
                                                      destNode = seeder, 
                                                      eventType = REQUEST_CONNECTION_INFO, 
                                                      info = None)))
            self.eventQueue.put((self.getRestartTime(),event(srcNode = src,
                                                             destNode = None,
                                                             eventType = RESTART,
                                                             info = None)))

        # CONNECT: A node is requesting to connect to another node.
        # 
        # src = node that is requesting the connection
        # dest = node that is receiving this request
        elif eventEntry.eventType == CONNECT:
            destHasRoom = len(dest.incomingCnxs) < MAX_INCOMING
            srcHasRoom = len(src.outgoingCnxs) < MAX_OUTGOING
            if dest.isOnline and dest.nodeType != DARK and destHasRoom and srcHasRoom:
                src.addToTried(dest.ipV4Addr, self.globalTime)

                dest.learnIP(src.ipV4Addr, src.ipV4Addr)
                dest.addToTried(src.ipV4Addr, self.globalTime)

                src.addToOutgoingCnxs(dest.ipV4Addr)
                dest.addToIncomingCnxs(src.ipV4Addr)

                # propagate reply ADDR message
                ipList = dest.selectAddrs()
                for ipSubList in ipList:
                    self.eventQueue.put((scheduledTime, event(srcNode = dest,
                                                              destNode = src,
                                                              eventType = CONNECTION_INFO,
                                                              info = (ADDR_MSG, ipSubList))))
            else:
                self.eventQueue.put((scheduledTime, event(srcNode = dest,
                                                          destNode = src,
                                                          eventType = CONNECTION_FAILURE,
                                                          info = None)))

        # CONNECTION_FAILURE: Notifies a node that its connection request failed.
        # 
        # src = the node that rejected the connection request
        # dest = the node whose request failed
        elif eventEntry.eventType == CONNECTION_FAILURE:
            dest.incrementFailedAttempts(src.ipV4Addr)

            numTriedEntries = sum([len(bucket) for bucket in dest.triedTable])
            numNewEntries = sum([len(bucket) for bucket in dest.newTable])
            rho = float(numTriedEntries) / numNewEntries
            omega = len(dest.outgoingCnxs)

            PrTried = (rho**0.5) * (9 - omega) 
            PrTried /= (omega + 1) + (rho**0.5) * (9 - omega) 
            table = dest.triedTable if random.random() < PrTried else dest.newTable

            numRejects = 0
            accepted = False
            ip = None

            if len(dest.outgoingCnxs) < MAX_OUTGOING:
              while not accepted:
                  bucketNum = random.randint(0, len(table) - 1)
                  if len(table[bucketNum]) > 0:
                      bucketPos = random.randint(0, len(table[bucketNum]) - 1)
                      ip = table[bucketNum].keys()[bucketPos]
                      timestamp = table[bucketNum][ip]
                      t = ((self.globalTime - timestamp) / 600) * 10
                      probAccept = min(1, (1.2**numRejects) / float(1+t))
                      accepted = random.random() < probAccept
                      if not accepted:
                          numRejects += 1

              self.eventQueue.put((scheduledTime, event(srcNode = dest,
                                                        destNode = self.ipToNodes[ip],
                                                        eventType = CONNECT,
                                                        info = None)))

        # REQUEST_CONNECTION_INFO: A node is requesting information about nodes 
        #                           to connect to. Simulates a DNS query to a seeder node.
        # 
        # src = the requesting node
        # dest = seeder node that will answer the request
        elif eventEntry.eventType == REQUEST_CONNECTION_INFO:
            if random.random() > SEEDER_REPLY_FAIL_RATE:
                # seeder has no issue
                ipList = dest.getIPsForQuery() # List of IPs returned by the seeder node from the DNS query
                self.eventQueue.put((scheduledTime, event(srcNode = dest, 
                                                          destNode = src, 
                                                          eventType = CONNECTION_INFO, 
                                                          info = (DNS_MSG, ipList))))

            else:
                # seeder timed out
                scheduledTime += WAIT_TIME_TO_CONCLUDE_REQUEST_LOST
                self.eventQueue.put((scheduledTime, event(srcNode = src,
                                                          destNode = None,
                                                          eventType = USE_HARDCODED_IPS,
                                                          info = None)))

        # CONNECTION_INFO: A node is receiving information about nodes to connect to.
        # 
        # src = node that sent the connection info
        # dest = node that is receiving the connection info
        # info = list of IP addresses to connect to
        elif eventEntry.eventType == CONNECTION_INFO:
            msgType, connections = eventEntry.info

            if msgType == ADDR_MSG:
                dest.addToKnownAddr(src.ipV4Addr)

                self.eventLog.append(CONNECTION_INFO_ADDR)

                if len(connections) >= MAX_ADDRS_PER_MSG:
                    dest.blacklistIP(src.ipV4Addr)
                elif len(connections) <= MAX_ADDRS_TO_FORWARD:
                    # forward same message to 2 peers
                    forwardedEvent = eventEntry
                    forwardedEvent._replace(srcNode = dest)

                    peerIpList = dest.selectPeersForAddrMsg(self.globalTime)
                    for ip in peerIpList:
                        peerNode = self.ipToNodes[ip]

                        forwardedEvent._replace(destNode = peerNode)
                        self.eventQueue.put((scheduledTime, forwardedEvent))

            if dest.isIpBlacklisted(src.ipV4Addr):
                # ensure this node-pair is not connected
                dest.removeFromConnections(src.ipV4Addr)
                src.removeFromConnections(dest.ipV4Addr)
            else:
                for ip in connections:
                    dest.learnIP(ip, src.ipV4Addr)
                    dest.addToNew(ip, self.globalTime)

                for i in range(MAX_OUTGOING - len(dest.outgoingCnxs)):
                    self.addCxns(dest, scheduledTime)

        # NEW_DAY: A node sends out ADDR messages to 2 peers with only its own ip
        #          and flushes its already sent to list.
        #          Also create event for tomorrow
        # 
        # src = None
        # dest = subject node
        elif eventEntry.eventType == NEW_DAY:
            if eventEntry.destNode == self.nodes[0]:
                print 'day ' + str(self.globalTime / ONE_DAY)
            dest.notifyNewDay(self.globalTime)

            ipList = [dest.ipV4Addr]

            # send ADDR_MSG to each peer
            connections = []
            connections.extend(dest.incomingCnxs)
            connections.extend(dest.outgoingCnxs)
            for ip in connections:
                thisNode = self.ipToNodes[ip]
                if thisNode is not None:
                    # no latency because node knows instantly when it's a new day
                    self.eventQueue.put((self.globalTime, event(srcNode = dest, 
                                                              destNode = thisNode, 
                                                              eventType = CONNECTION_INFO, 
                                                              info = (ADDR_MSG, ipList))))

            # place NEW_DAY event for tomorrow
            self.eventQueue.put((self.globalTime + ONE_DAY, eventEntry))

        # USE_HARDCODED_IPS: Seeder timed out, attempt connections from hardcoded list of IPs.
        #
        # src = subject node
        # dest = None
        elif eventEntry.eventType == USE_HARDCODED_IPS:
            # seeder timed out, use hardcoded IPs for connections
            for ip in self.hardcodedIPs:
                src.learnIP(ip, HARDCODED_IP_SOURCE)
                src.addToNew(ip, self.globalTime)

            for i in range(MAX_OUTGOING - len(src.outgoingCnxs)):
                self.addCxns(src, scheduledTime)

        # AFTER_REJOIN_MAYBE_REQUEST_SEEDER: After rejoining, the src node attempted to make connections
        #                                    based on its table entries. This event arises 11 seconds
        #                                    after the REJOIN event. If less than 2 outgoing connections
        #                                    have been made, query a seeder.
        #
        # src = subject node
        # dest = None
        elif eventEntry.eventType == AFTER_REJOIN_MAYBE_REQUEST_SEEDER:
            if len(src.outgoingCnxs) < 2:
                seeder = self.seederNodes[random.randint(0, NUM_SEEDERS - 1)]
                self.eventQueue.put((scheduledTime, event(srcNode = src,
                                                          destNode = seeder,
                                                          eventType = REQUEST_CONNECTION_INFO,
                                                          info = None)))

        else:
            raise Exception("Invalid event type")
        return self.globalTime
    
    # Return a graph of the network
    # TODO Maybe this could be constructed incrementally?
    def getGraph(self):
        graph = nx.Graph()
        # import time
        # start = time.time()

        '''
        adj_list = []
        for node in self.nodes:
            for inConn in node.incomingCnxs:
              adj_list.append((inConn, node.ipV4Addr))
            for outConn in node.outgoingCnxs:
              adj_list.append((node.ipV4Addr, outConn))
        open('adj_list.tsv', 'w').write('\n'.join(['{} {}'.format(x, y) for (x, y) in adj_list]))
        graph = nx.read_adjlist('adj_list.tsv')
        '''
        
        for node in self.nodes:
            graph.add_node(node.ipV4Addr)
        for node in self.nodes:
            for inConn in node.incomingCnxs:
                graph.add_edge(inConn, node.ipV4Addr, key=0)
            for outConn in node.outgoingCnxs:
                graph.add_edge(node.ipV4Addr, outConn, key=0)

        # end = time.time()
        # print('Graph created in {} seconds.'.format(end - start))
        return graph 

    # Draw graph of network nodes out to file
    def drawGraph(self, mode = GRAPH_SAMPLE_ALL, filename = 'graph.jpg'):
        graph = self.getGraph()
        if mode is GRAPH_SAMPLE_ALL: 
          pass
        # Random subset of nodes & their associated edges
        elif mode is GRAPH_SAMPLE_RND:
          newGraph = nx.Graph()
          included = set([])
          for node in graph:
            if random.random() < GRAPH_SAMPLE_RND_RATIO:
              newGraph.add_node(node)
              included.add(node)
          for node in graph:
            for neighbor in graph.neighbors(node):
              if node in included and neighbor in included:
                newGraph.add_edge(node, neighbor, key = 0)
          graph = newGraph
        # Just draw the largest connected component
        elif mode is GRAPH_SAMPLE_LCC:
          connected = list(nx.connected_components(graph))
          lcc = list(max(connected, key = len))
          newGraph = nx.Graph()
          for node in lcc:
              newGraph.add_node(node)
          for node in lcc:
              for neighbor in graph.neighbors(node):
                  newGraph.add_edge(node, neighbor, key = 0)
          graph = newGraph 
        nx.draw(graph)
        plt.savefig(filename)

    # Draw eccentricity histogram out to file
    # NOTE: Uses largest connected component to ensure all nodes have finite eccentricity
    def drawEccentricity(self, filename = 'eccentricity.png'):
        graph = self.getLCC()
        eccentricities = [x[1] for x in nx.eccentricity(graph).items()]
        unique = set(eccentricities)
        counts = sorted([(v, eccentricities.count(v)) for v in unique], key = lambda x:x[0])
        xs = [x[0] for x in counts]
        ys = [x[1] for x in counts]
        print(xs, ys)
        plt.xlabel('Eccentricity')
        plt.ylabel('Node Count')
        plt.bar(xs, ys)
        plt.savefig(filename)

    # Termination Condition: Global Time
    # Terminate once the network has persisted for a certain length of time.
    def getGlobalTime(self):
        return self.globalTime

    # Termination Condition: # Nodes
    # Terminate once the network has reached a certain size.
    def getNumNodes(self):
        return len(self.nodes)

    # Termination Condition: Diameter
    # Terminate once the network has reached a given diameter.
    def getDiameter(self):
        graph = self.getGraph()
        try:
            diameter = nx.diameter(graph)
        # NetworkX will throw an exception if the graph is not connected (~ infinite diameter)
        except nx.NetworkXError:
            return -1

    # Graph Minimum Cut
    # Number of edges present in the minimum edge cut
    def getMinCut(self):
        graph = self.getGraph()
        try: 
          min_cut = nx.minimum_edge_cut(graph)
        except: # not connected
          return -1
        return len(min_cut)

    def getLCC(self):
        graph = self.getGraph()
        connected = list(nx.connected_components(graph))
        if len(connected) == 0:
          return -1
        lcc = list(max(connected, key = len))
        newGraph = nx.Graph()
        for node in lcc:
            newGraph.add_node(node)
        for node in lcc:
            for neighbor in graph.neighbors(node):
                newGraph.add_edge(node, neighbor, key = 0)
        return newGraph
 
    # Termination Condition: Diameter of largest connected component
    # Terminate once the network's largest connected component has reached a given diameter
    # (in case the network isn't connected)
    def getLCCDiameter(self):
       return nx.diameter(self.getLCC())

    def shouldTerminate(self, condition, value):
        if condition == TERMINATION_COND_TIME:
            return self.getGlobalTime() >= value
        elif condition == TERMINATION_COND_NUM_NODES:
            return self.getNumNodes() >= value
        elif condition == TERMINATION_COND_DIAMETER:
            return self.getDiameter() >= value
        elif condition == TERMINATION_COND_LCC_DIAMETER:
            return self.getLCCDiameter() >= value
        else:
            raise Exception('Unknown termination condition!')
