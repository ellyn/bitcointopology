import unittest
import mock

from node import Node
from network import Network
import Queue
from network import event
from constants import *

# python testNode.py
# ^ runs all testcases in this file

class TestNode(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.network = Network()

        # empty eventQueue
        self.network.eventQueue = Queue.PriorityQueue()

        # find free non-dark nodes
        foundFirst = False
        for i in range(len(self.network.nodes)):
            thisNode = self.network.nodes[i]
            if(thisNode.nodeType == PEER):
                if not foundFirst:
                    self.nodePeer = thisNode
                    self.nodePeerIndex = i
                    foundFirst = True
                else:
                    self.nodePeer2 = thisNode
                    self.nodePeer2Index = i
                    break;

        self.seederNode = self.network.seederNodes[0]

        self.sourceIP = self.network.assignIP()

    def setUp(self):
        # mock network.getRestartTime() so that event stays out of the way
        self.network.getRestartTime = mock.Mock(return_value = 999)

        # empty eventQueue
        self.network.eventQueue = Queue.PriorityQueue()

        # reset some nodes
        oldIP = self.nodePeer.ipV4Addr
        del self.network.ipToNodes[oldIP]
        self.nodePeer = Node(oldIP)
        self.nodePeer.isOnline = True
        self.network.ipToNodes[oldIP] = self.nodePeer
        self.network.ipToNonDarkNodes[oldIP] = self.nodePeer
        self.network.nodes[self.nodePeerIndex] = self.nodePeer

        oldIP = self.nodePeer2.ipV4Addr
        del self.network.ipToNodes[oldIP]
        self.nodePeer2 = Node(oldIP)
        self.nodePeer2.isOnline = True
        self.network.ipToNodes[oldIP] = self.nodePeer2
        self.network.ipToNonDarkNodes[oldIP] = self.nodePeer2
        self.network.initNodes[self.nodePeer2Index] = self.nodePeer2

    # test method names must start with "test..."

    # Headers reference section from paper
    
    # 2
    def test_whenNodeReceivesIncomingConnectionRequest_doesNotExceedMaxIncomingConnections_andGeneratesConnectionFailureEvent(self):
        # generate node with max incoming connections
        for ip in [self.network.assignIP() for i in range(MAX_INCOMING)]:
            self.nodePeer.incomingCnxs.append(ip)
            self.nodePeer.learnIP(ip, self.sourceIP)

        # communicating nodes have heard of each other before
        self.nodePeer.learnIP(self.nodePeer2.ipV4Addr, self.sourceIP)
        self.nodePeer2.learnIP(self.nodePeer.ipV4Addr, self.sourceIP)

        # add CONNECT event to network.eventQueue as only existing event
        connectEvent = event(srcNode=self.nodePeer2, destNode=self.nodePeer, eventType=CONNECT, info=None)
        self.network.eventQueue.put((self.network.globalTime, connectEvent))

        # mock eventQueue.put from here forward so we can monitor when it is called
        self.network.eventQueue.put = mock.Mock()
        # mock randomness out
        latency = 0.1
        self.network.generateLatency = mock.Mock(return_value=latency)

        # collect data, process event, collect data
        numConnectionsBefore = len(self.nodePeer.incomingCnxs)
        self.network.processNextEvent()
        numConnectionsAfter = len(self.nodePeer.incomingCnxs)
        
        # assert data correct and monitored method called as expected
        self.assertEqual(numConnectionsBefore, numConnectionsAfter)
        self.network.eventQueue.put.assert_called_once_with((self.network.globalTime+latency, event(srcNode=self.nodePeer, destNode=self.nodePeer2, eventType=CONNECTION_FAILURE, info=None)))
    
    def test_whenNodeMakesOutgoingConnectionRequest_doesNotExceedMaxOutgoingConnections(self):
        # generate node with max outgoing connections
        for ip in [self.network.assignIP() for i in range(MAX_OUTGOING)]:
            self.nodePeer.outgoingCnxs.append(ip)
            self.nodePeer.learnIP(ip, self.sourceIP)

        # communicating nodes have heard of each other before
        self.nodePeer.learnIP(self.nodePeer2.ipV4Addr, self.sourceIP)
        self.nodePeer2.learnIP(self.nodePeer.ipV4Addr, self.sourceIP)

        # add CONNECT event to network.eventQueue as only existing event
        connectEvent = event(srcNode=self.nodePeer, destNode=self.nodePeer2, eventType=CONNECT, info=None)
        self.network.eventQueue.put((self.network.globalTime, connectEvent))

        # mock eventQueue.put from here forward so we can monitor when it is called
        self.network.eventQueue.put = mock.Mock()
        # mock randomness out
        latency = 0.1
        self.network.generateLatency = mock.Mock(return_value=latency)

        # collect data, process event, collect data
        numConnectionsBefore = len(self.nodePeer.outgoingCnxs)
        self.network.processNextEvent()
        numConnectionsAfter = len(self.nodePeer.outgoingCnxs)
        
        # assert data correct and monitored method called as expected
        self.assertEqual(numConnectionsBefore, numConnectionsAfter)
        self.network.eventQueue.put.assert_called_once_with((self.network.globalTime+latency, event(srcNode=self.nodePeer2, destNode=self.nodePeer, eventType=CONNECTION_FAILURE, info=None)))
    
    # 2.1 DNS Seeders
    @mock.patch('network.SEEDER_REPLY_FAIL_RATE', -1.0)
    def test_whenNodeJoinsNetwork_receivesIPsFromSeeder(self):
        # patch constant SEEDER_REPLY_FAIL_RATE so we automatically decide seeder does not timeout

        joinEvent = event(srcNode = self.nodePeer, destNode = None, eventType = JOIN, info = None)
        self.network.eventQueue.put((0, joinEvent))

        newTableSizeBefore = sum([len(b) for b in self.nodePeer.newTable])
        triedTableSizeBefore = sum([len(b) for b in self.nodePeer.triedTable])

        # process JOIN
        self.network.processNextEvent()
        
        # get a hold of seeder node, place event back in eventQueue
        eventTime, reqConInfoEvent = self.network.eventQueue.get()
        self.assertEquals(reqConInfoEvent.eventType, REQUEST_CONNECTION_INFO)
        self.seederNode = reqConInfoEvent.destNode
        self.network.eventQueue.put((eventTime, reqConInfoEvent))

        # process REQUEST_CONNECTION_INFO and CONNECTION_INFO
        self.network.processNextEvent()
        self.network.processNextEvent()

        newTableSizeAfter = sum([len(b) for b in self.nodePeer.newTable])
        triedTableSizeAfter = sum([len(b) for b in self.nodePeer.triedTable])

        # assert all new table entries from seeder
        for ip in self.nodePeer.ipToAddr.keys():
            sourceIP = self.nodePeer.ipToAddr[ip].sourceIP
            self.assertEqual(sourceIP, self.seederNode.ipV4Addr)

            self.assertTrue(ip in self.seederNode.knownIPs)
        self.assertEqual(newTableSizeBefore + DNS_QUERY_SIZE, newTableSizeAfter)

        # assert tried table remains empty
        self.assertEqual(triedTableSizeBefore, 0)
        self.assertEqual(triedTableSizeAfter, 0)
    
    @mock.patch('network.SEEDER_REPLY_FAIL_RATE', 2.0)
    def test_whenNodeJoinsNetwork_andSeederFailsToReply_usesHardcodedIPs(self):
        # patch constant SEEDER_REPLY_FAIL_RATE so we automatically decide seeder will timeout

        joinEvent = event(srcNode=self.nodePeer, destNode=None, eventType=JOIN, info=None)
        self.network.eventQueue.put((0, joinEvent))

        newTableSizeBefore = sum([len(b) for b in self.nodePeer.newTable])
        triedTableSizeBefore = sum([len(b) for b in self.nodePeer.triedTable])

        # process JOIN
        self.network.processNextEvent()

        # remove RESTART event
        time1, event1 = self.network.eventQueue.get()
        time2, event2 = self.network.eventQueue.get()
        if event1.eventType == REQUEST_CONNECTION_INFO:
            self.network.eventQueue.put((time1, event1))
        else:
            self.network.eventQueue.put((time2, event2))

        # process REQUEST_CONNECTION_INFO and USE_HARDCODED_IPS events
        self.network.processNextEvent()
        self.network.processNextEvent()

        newTableSizeAfter = sum([len(b) for b in self.nodePeer.newTable])
        triedTableSizeAfter = sum([len(b) for b in self.nodePeer.triedTable])

        # assert all IPs in new table from HARDCODED_IP_SOURCE and network's hardcoded ip list
        for ip in self.nodePeer.ipToAddr.keys():
            sourceIP = self.nodePeer.ipToAddr[ip].sourceIP
            self.assertEqual(sourceIP, HARDCODED_IP_SOURCE)

            self.assertTrue(ip in self.network.hardcodedIPs)
        self.assertEqual(newTableSizeBefore + len(self.network.hardcodedIPs), newTableSizeAfter)

        # assert tried table remains empty
        self.assertEqual(triedTableSizeBefore, 0)
        self.assertEqual(triedTableSizeAfter, 0)

        # assert MAX_OUTGOING connect events in eventQueue, all with source nodePeer, dest ip in hardcoded_list
        self.assertEqual(self.network.eventQueue.qsize(), MAX_OUTGOING)
        for i in range(MAX_OUTGOING):
            timestamp, thisEvent = self.network.eventQueue.get()
            
            self.assertEqual(thisEvent.eventType, CONNECT)
            self.assertEqual(thisEvent.srcNode, self.nodePeer)
            self.assertTrue(thisEvent.destNode.ipV4Addr in self.network.hardcodedIPs)

    @mock.patch('network.MAX_OUTGOING', 0)
    def test_whenNodeRestarts_andNodeHasLessThanTwoOutgoingConnections_andElevenSecondsElapsed_receivesIPsFromSeeder(self):
        # patch MAX_OUTGOING instances in network.py so our node doesnt make any connections

        self.nodePeer.learnIP(self.nodePeer2.ipV4Addr, self.sourceIP)
        self.nodePeer.addToTried(self.nodePeer2.ipV4Addr, 0)
        
        restartEvent = event(srcNode=self.nodePeer, destNode=None, eventType=RESTART, info=None)
        self.network.eventQueue.put((0, restartEvent))

        # process RESTART event
        self.network.processNextEvent()

        # get time of REJOIN, place back in eventQueue
        rejoinTime, rejoinEvent = self.network.eventQueue.get()
        self.assertEqual(rejoinEvent.eventType, REJOIN)
        self.network.eventQueue.put((rejoinTime, rejoinEvent))

        # process REJOIN, AFTER_REJOIN_MAYBE_REQUEST_SEEDER events
        self.network.processNextEvent()
        self.network.processNextEvent()

        nextTime, nextEvent = self.network.eventQueue.get()

        # assert seeder request more than 11 seconds from rejoin event
        self.assertTrue(rejoinTime + 11 <= nextTime)

        # assert correct nodes involved in REQUEST_CONNECTION_INFO event
        self.assertEqual(nextEvent.srcNode, self.nodePeer)
        self.assertTrue(nextEvent.destNode in self.network.seederNodes)
        self.assertEqual(nextEvent.eventType, REQUEST_CONNECTION_INFO)
    
    # 2.1 ADDR
    def test_whenAddrMsgReceivedWithMoreThanThousand_sendingNodeBlacklisted(self):
        self.assertTrue(True)

    @mock.patch('node.Node.selectAddrs')
    def test_whenBlacklistedNodeAttemptsToConnect_ignoreIt(self, mock_node_selectAddrs):
        # patch node.selectAddrs() to return too many addresses such that another node will blacklist it
        tooManyIPs = [[self.network.assignIP() for _ in range(MAX_ADDRS_PER_MSG+1)]]
        mock_node_selectAddrs.return_value = tooManyIPs

        # take measurements before
        totalConnectionsBefore1 = sum(self.nodePeer.incomingCnxs) + sum(self.nodePeer.outgoingCnxs)
        totalConnectionsBefore2 = sum(self.nodePeer2.incomingCnxs) + sum(self.nodePeer2.outgoingCnxs)
        newTableSizeBefore = sum([len(b) for b in self.nodePeer.newTable])
        triedTableSizeBefore = sum([len(b) for b in self.nodePeer.triedTable])

        # prepare nodes for CONNECT
        self.nodePeer.learnIP(self.nodePeer2.ipV4Addr, self.sourceIP)
        self.nodePeer2.learnIP(self.nodePeer.ipV4Addr, self.sourceIP)

        # prepare eventQueue
        connectEvent = event(srcNode=self.nodePeer, destNode=self.nodePeer2, eventType=CONNECT, info=None)
        self.network.eventQueue.put((self.network.globalTime, connectEvent))

        # process CONNECT, CONNECTION_INFO events
        self.network.processNextEvent()
        self.network.processNextEvent()

        # assert ip is blacklisted
        self.assertTrue(self.nodePeer2.ipV4Addr in self.nodePeer.blacklistedIPs)

        # assert no connections kept
        totalConnectionsAfter1 = sum(self.nodePeer.incomingCnxs) + sum(self.nodePeer.outgoingCnxs)
        totalConnectionsAfter2 = sum(self.nodePeer2.incomingCnxs) + sum(self.nodePeer2.outgoingCnxs)
        self.assertEqual(totalConnectionsBefore1, totalConnectionsAfter1)
        self.assertEqual(totalConnectionsBefore2, totalConnectionsAfter2)

        # assert nothing was added to new table
        newTableSizeAfter = sum([len(b) for b in self.nodePeer.newTable])
        triedTableSizeAfter = sum([len(b) for b in self.nodePeer.triedTable])
        self.assertEqual(newTableSizeBefore, newTableSizeAfter)
        self.assertEqual(triedTableSizeBefore + 1, triedTableSizeAfter)

        # assert nodePeer's tried table only contains blacklisted ip
        flattenedIPs = []
        for bucket in self.nodePeer.triedTable:
            flattenedIPs.extend(bucket.keys())
        self.assertEqual(len(flattenedIPs), 1)
        self.assertTrue(self.nodePeer2.ipV4Addr in flattenedIPs)
    
    def test_whenOutgoingConnectionEstablishedWithPeer_receiveAddrMsgFromPeer(self):
        # prepare nodes for CONNECT
        self.nodePeer.learnIP(self.nodePeer2.ipV4Addr, self.sourceIP)
        self.nodePeer2.learnIP(self.nodePeer.ipV4Addr, self.sourceIP)
        # populate nodePeer2's tables with some IPs (that will be sent in ADDR)
        someIPs = [self.network.assignIP() for _ in range(100)]
        for ip in someIPs[:50]:
            self.nodePeer2.learnIP(ip, self.sourceIP)
            self.nodePeer2.addToTried(ip, 0)
        for ip in someIPs[50:]:
            self.nodePeer2.learnIP(ip, self.sourceIP)
            self.nodePeer2.addToNew(ip, 0)

        # prepare eventQueue
        connectEvent = event(srcNode=self.nodePeer, destNode=self.nodePeer2, eventType=CONNECT, info=None)
        self.network.eventQueue.put((self.network.globalTime, connectEvent))

        # process CONNECT event
        self.network.processNextEvent()

        # assert generated event is ADDR between correct nodes
        nextTime, nextEvent = self.network.eventQueue.get()
        self.assertEqual(nextEvent.eventType, CONNECTION_INFO)
        self.assertEqual(nextEvent.srcNode, self.nodePeer2)
        self.assertEqual(nextEvent.destNode, self.nodePeer)
        self.assertEqual(nextEvent.info[0], ADDR_MSG)

        # assert sent IPs come from nodePeer2's tables
        flattenedIPs = []
        for bucket in self.nodePeer2.triedTable:
            flattenedIPs.extend(bucket.keys())
        for bucket in self.nodePeer2.newTable:
            flattenedIPs.extend(bucket.keys())
        [self.assertTrue(ip in flattenedIPs) for ip in nextEvent.info[1]]
        
    # 2.2 Tried table
    def test_whenSelectingBucketForAnIp_useSchemeFromPaper(self):
        self.nodePeer.nonce = 'some nonce'
        peerIP = self.network.assignIP()

        temp = peerIP.split('.')
        peerGroup = temp[0] + '.' + temp[1]
        nonce = str(self.nodePeer.nonce)
        i = hash(nonce + peerIP) % 4
        expectedBucketNum = hash(nonce + peerGroup + str(i)) % 64

        bucketNum = self.nodePeer.mapToTriedBucket(peerIP)

        self.assertEqual(expectedBucketNum, bucketNum)
    
    def test_whenConnectSuccessToPeer_peerAddressInsertedIntoTried(self):
        # generate node with space for at least 1 new connection
        self.sourceIP = self.network.assignIP()
        for ip in [self.network.assignIP() for i in range(MAX_OUTGOING - random.randint(1, MAX_OUTGOING))]:
            self.nodePeer.outgoingCnxs.append(ip)
            self.nodePeer.learnIP(ip, self.sourceIP)

        # communicating nodes have heard of each other before
        self.nodePeer.learnIP(self.nodePeer2.ipV4Addr, self.sourceIP)
        self.nodePeer2.learnIP(self.nodePeer.ipV4Addr, self.sourceIP)

        # add CONNECT event to network.eventQueue as only existing event
        connectEvent = event(srcNode=self.nodePeer, destNode=self.nodePeer2, eventType=CONNECT, info=None)
        self.network.eventQueue.put((self.network.globalTime, connectEvent))

        # collect data, process event, collect data
        peerIP = self.nodePeer2.ipV4Addr
        bucket = self.nodePeer.mapToTriedBucket(peerIP)

        isPeerInTriedTableBefore = (peerIP in self.nodePeer.triedTable[bucket])
        self.network.processNextEvent()
        isPeerInTriedTableAfter = (peerIP in self.nodePeer.triedTable[bucket])
        
        # assert data correct
        self.assertFalse(isPeerInTriedTableBefore)
        self.assertTrue(isPeerInTriedTableAfter)
    
    def test_whenInsertingNewAddressAndBucketFull_properEvictionPerformed(self):
        SEED = 567
        SOURCE_IP = self.network.assignIP()

        peerIP = self.network.assignIP()
        peerTimestamp = random.random() + 10
        self.nodePeer.learnIP(peerIP, SOURCE_IP)
        bucketNum = self.nodePeer.mapToTriedBucket(peerIP)

        while len(self.nodePeer.triedTable[bucketNum]) < ADDRESSES_PER_BUCKET:
            ip = self.network.assignIP()
            timestamp = random.random()
            self.nodePeer.learnIP(ip, SOURCE_IP)
            self.nodePeer.triedTable[bucketNum][ip] = timestamp

        random.seed(SEED)
        # determine which IP is expected to be evicted
        fourIPs = random.sample(self.nodePeer.triedTable[bucketNum], 4)
        fourTimestamps = [self.nodePeer.triedTable[bucketNum][ip] for ip in fourIPs]
        
        oldestTimestamp = 999
        for i, timestamp in enumerate(fourTimestamps):
            if timestamp < oldestTimestamp:
                oldestTimestamp = timestamp
                oldestIp = fourIPs[i]

        random.seed(SEED)
        self.nodePeer.addToTried(peerIP, peerTimestamp)

        self.assertEqual(len(self.nodePeer.triedTable[bucketNum]), ADDRESSES_PER_BUCKET)
        self.assertTrue(peerIP in self.nodePeer.triedTable[bucketNum].keys())
        self.assertFalse(oldestIp in self.nodePeer.triedTable[bucketNum].keys())
    
    def test_whenInsertingIntoTriedAndPeerAddressAlreadyPresent_onlyTimestampUpdated(self):
        # generate node already connected to peer
        peerIP = self.nodePeer2.ipV4Addr
        bucket = self.nodePeer.mapToTriedBucket(peerIP)
        
        self.nodePeer.outgoingCnxs.append(peerIP)
        self.nodePeer.learnIP(peerIP, self.sourceIP)
        self.nodePeer.triedTable[bucket][peerIP] = self.network.globalTime

        # collect data before
        peerTimestampBefore = self.nodePeer.triedTable[bucket][peerIP]
        triedTableTotalEntriesBefore = sum([len(b) for b in self.nodePeer.triedTable])
        numPeerIpOccurencesBefore = sum([b.keys() for b in self.nodePeer.triedTable], []).count(peerIP)

        # perform action
        self.nodePeer.addToTried(peerIP, self.network.globalTime+1)
        
        # collect data after
        peerTimestampAfter = self.nodePeer.triedTable[bucket][peerIP]
        triedTableTotalEntriesAfter = sum([len(b) for b in self.nodePeer.triedTable])
        numPeerIpOccurencesAfter = sum([b.keys() for b in self.nodePeer.triedTable], []).count(peerIP)
        
        # assertions
        self.assertTrue(peerTimestampBefore < peerTimestampAfter)
        self.assertEqual(triedTableTotalEntriesBefore, triedTableTotalEntriesAfter)
        self.assertEqual(numPeerIpOccurencesBefore, 1)
        self.assertEqual(numPeerIpOccurencesAfter, 1)
    
    # 2.2 New table
    def test_whenAddressFromDnsSeeder_onlyAddedToNewTable(self):
        ip = self.network.assignIP()
        self.nodePeer2.ipV4Addr = ip
        self.network.ipToNodes[ip] = self.nodePeer2
        self.nodePeer.nonce = 'some nonce'
        
        # fill nodePeer's outgoing connection to force ip into new table
        for i in range(MAX_OUTGOING):
            outIp = self.network.assignIP()
            self.nodePeer.outgoingCnxs.append(outIp)

        connectionInfoEvent = event(srcNode=self.seederNode, destNode=self.nodePeer, eventType=CONNECTION_INFO, info=(DNS_MSG, [ip]))
        self.network.eventQueue.put((self.network.globalTime, connectionInfoEvent))

        self.nodePeer.learnIP(ip, self.seederNode.ipV4Addr)

        # run code (CONNECTION_INFO, and CONNECT)
        self.network.processNextEvent()

        # verify ip appears in new table and not tried table
        foundInNew = False
        for bucketNum, addressDictionary in enumerate(self.nodePeer.newTable):
            if ip in addressDictionary.keys():
                foundInNew = True

        foundInTried = False
        for bucketNum, addressDictionary in enumerate(self.nodePeer.triedTable):
            if ip in addressDictionary.keys():
                foundInTried = True

        self.assertTrue(foundInNew)
        self.assertFalse(foundInTried)

    def test_whenSelectingBucket_useSchemeFromPaper(self):
        ip = self.network.assignIP()
        self.nodePeer2.ipV4Addr = ip
        self.network.ipToNodes[ip] = self.nodePeer2
        self.nodePeer.nonce = 'some nonce'
        
        # fill nodePeer's outgoing connection to force ip into new table
        for i in range(MAX_OUTGOING):
            outIp = self.network.assignIP()
            self.nodePeer.outgoingCnxs.append(outIp)

        connectionInfoEvent = event(srcNode=self.seederNode, destNode=self.nodePeer, eventType=CONNECTION_INFO, info=(DNS_MSG, [ip]))
        self.network.eventQueue.put((self.network.globalTime, connectionInfoEvent))

        self.nodePeer.learnIP(ip, self.seederNode.ipV4Addr)
        sourceIp = self.nodePeer.ipToAddr[ip].sourceIP

        # compute bucket manually
        ipTemp = ip.split('.')
        ipGroup = ipTemp[0] + '.' + ipTemp[1]

        sourceTemp = sourceIp.split('.')
        srcIPGroup = sourceTemp[0] + '.' + sourceTemp[1] 

        nonce = str(self.nodePeer.nonce)
        i = hash(nonce + ipGroup + srcIPGroup) % 32
        expectedBucket = hash(nonce + srcIPGroup + str(i)) % 256
        
        # run code
        self.network.processNextEvent()

        # verify bucket
        actualBucket = []
        for bucketNum, addressDictionary in enumerate(self.nodePeer.newTable):
            if ip in addressDictionary.keys():
                actualBucket.append(bucketNum)

        self.assertEqual(len(actualBucket), 1)
        self.assertEqual(actualBucket[0], expectedBucket)

    def test_whenHashingGroupSourceGroupPair_hashesToUniqueBucket(self):
        differentIPs = 10
        numTrials = 10

        for i in range(differentIPs):
            ip = self.network.assignIP()
            peerIP = self.network.assignIP()

            bucketSet = set()
            for j in range(numTrials):
                computedBucket = self.nodePeer.mapToNewBucket(ip, peerIP)
                bucketSet.add(computedBucket)
            self.assertEqual(len(bucketSet), 1)

    def test_whenInsertingAndBucketFull_andTerribleNodeExistsAgewise_properEvictionPerformed(self):
        SOURCE_IP = self.network.assignIP()

        peerIP = self.network.assignIP()
        peerTimestamp = random.random() + THIRTY_DAYS + 1
        self.nodePeer.learnIP(peerIP, SOURCE_IP)
        bucketNum = self.nodePeer.mapToNewBucket(peerIP, SOURCE_IP)

        while len(self.nodePeer.newTable[bucketNum]) < (ADDRESSES_PER_BUCKET - 1):
            ip = self.network.assignIP()
            timestamp = random.random() + THIRTY_DAYS
            self.nodePeer.learnIP(ip, SOURCE_IP)
            self.nodePeer.newTable[bucketNum][ip] = timestamp

        # add terrible node (over 30 days old)
        while len(self.nodePeer.newTable[bucketNum]) < ADDRESSES_PER_BUCKET:
            terribleIp = self.network.assignIP()
            timestamp = random.random()
            self.nodePeer.learnIP(terribleIp, SOURCE_IP)
            self.nodePeer.newTable[bucketNum][terribleIp] = timestamp

        self.nodePeer.addToNew(peerIP, peerTimestamp)

        self.assertEqual(len(self.nodePeer.newTable[bucketNum]), ADDRESSES_PER_BUCKET)
        self.assertTrue(peerIP in self.nodePeer.newTable[bucketNum].keys())
        self.assertFalse(terribleIp in self.nodePeer.newTable[bucketNum].keys())

    def test_whenInsertingAndBucketFull_andTerribleNodeExistsByFailedAttempts_properEvictionPerformed(self):
        SOURCE_IP = self.network.assignIP()

        peerIP = self.network.assignIP()
        peerTimestamp = random.random()
        self.nodePeer.learnIP(peerIP, SOURCE_IP)
        bucketNum = self.nodePeer.mapToNewBucket(peerIP, SOURCE_IP)

        while len(self.nodePeer.newTable[bucketNum]) < ADDRESSES_PER_BUCKET:
            ip = self.network.assignIP()
            timestamp = random.random()
            self.nodePeer.learnIP(ip, SOURCE_IP)
            self.nodePeer.newTable[bucketNum][ip] = timestamp

        # modify last node as the terrible node
        terribleIp = ip
        for i in range(MAX_RETRIES + 1):
            self.nodePeer.incrementFailedAttempts(terribleIp)

        self.nodePeer.addToNew(peerIP, peerTimestamp)

        self.assertEqual(len(self.nodePeer.newTable[bucketNum]), ADDRESSES_PER_BUCKET)
        self.assertTrue(peerIP in self.nodePeer.newTable[bucketNum].keys())
        self.assertFalse(terribleIp in self.nodePeer.newTable[bucketNum].keys())

    def test_whenInsertingAndBucketFull_andThoseNodesAreNotTerrible_properEvictionPerformed(self):
        SEED = 567
        SOURCE_IP = self.network.assignIP()

        peerIP = self.network.assignIP()
        peerTimestamp = random.random() + 10
        self.nodePeer.learnIP(peerIP, SOURCE_IP)
        bucketNum = self.nodePeer.mapToNewBucket(peerIP, SOURCE_IP)

        while len(self.nodePeer.newTable[bucketNum]) < ADDRESSES_PER_BUCKET:
            ip = self.network.assignIP()
            timestamp = random.random()
            self.nodePeer.learnIP(ip, SOURCE_IP)
            self.nodePeer.newTable[bucketNum][ip] = timestamp

        random.seed(SEED)
        # determine which IP is expected to be evicted
        fourIPs = random.sample(self.nodePeer.newTable[bucketNum], 4)
        fourTimestamps = [self.nodePeer.newTable[bucketNum][ip] for ip in fourIPs]
        
        oldestTimestamp = 999
        for i, timestamp in enumerate(fourTimestamps):
            if timestamp < oldestTimestamp:
                oldestTimestamp = timestamp
                oldestIp = fourIPs[i]

        random.seed(SEED)
        self.nodePeer.addToNew(peerIP, peerTimestamp)

        self.assertEqual(len(self.nodePeer.newTable[bucketNum]), ADDRESSES_PER_BUCKET)
        self.assertTrue(peerIP in self.nodePeer.newTable[bucketNum].keys())
        self.assertFalse(oldestIp in self.nodePeer.newTable[bucketNum].keys())
    
if __name__ == '__main__':
    unittest.main()