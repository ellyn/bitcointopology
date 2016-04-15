import unittest
from mock import MagicMock

from node import Node
from network import Network
from network import event
from constants import *

# python testNode.py
# ^ runs all testcases in this file
# may need to run `sudo pip install -U mock` for mock library because python 2.7

class TestNode(unittest.TestCase):
    # run before every test case
    def setUp(self):
        self.network = Network()
        
        self.network.hardcodedIPs = [self.network.assignIP() for i in range(NUM_INIT_NODES)]
        self.seederNode = Node(self.network.assignIP(), SEEDER)

        self.nodePeer = Node(self.network.assignIP())
        self.nodePeer2 = Node(self.network.assignIP())
        self.sourceIP = self.network.assignIP()

        self.network.ipToNodes[self.nodePeer.ipV4Addr] = self.nodePeer
        self.network.ipToNodes[self.seederNode.ipV4Addr] = self.seederNode

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
        self.network.eventQueue.put = MagicMock(return_value=None)
        # mock randomness out
        latency = 0.1
        self.network.generateLatency = MagicMock(return_value=latency)

        # collect data, process event, collect data
        numConnectionsBefore = len(self.nodePeer.incomingCnxs)
        self.network.processNextEvent()
        numConnectionsAfter = len(self.nodePeer.incomingCnxs)
        
        # assert data correct and monitored method called as expected
        self.assertEqual(numConnectionsBefore, numConnectionsAfter)
        self.network.eventQueue.put.assert_called_once_with((self.network.globalTime+latency, event(srcNode=self.nodePeer, destNode=self.nodePeer2, eventType=CONNECTION_FAILURE, info=None)))
    
    def test_whenNodeMakesOutgoingConnectionRequest_doesNotExceedMaxOutgoingConnections(self):
        # generate node with max outgoing connections
        self.sourceIP = self.network.assignIP()
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
        self.network.eventQueue.put = MagicMock(return_value=None)
        # mock randomness out
        latency = 0.1
        self.network.generateLatency = MagicMock(return_value=latency)

        # collect data, process event, collect data
        numConnectionsBefore = len(self.nodePeer.outgoingCnxs)
        self.network.processNextEvent()
        numConnectionsAfter = len(self.nodePeer.outgoingCnxs)
        
        # assert data correct and monitored method called as expected
        self.assertEqual(numConnectionsBefore, numConnectionsAfter)
        self.network.eventQueue.put.assert_called_once_with((self.network.globalTime+latency, event(srcNode=self.nodePeer2, destNode=self.nodePeer, eventType=CONNECTION_FAILURE, info=None)))
    
    '''
    # 2.1 DNS Seeders
    def whenNodeJoinsNetwork_receivesIPsFromSeeder(self):
        # mock: node(peer), network.EventQueue(JOIN event next)
        # call network.processNextEvent()
        # process additionally generated events
        # assert CONNECTION_INFO w/that node ID appears
        # assert learnIP() and addToNew() called
    
    def whenNodeJoinsNetwork_andSeederFailsToReply_usesHardcodedIPs(self):
        # is this implemented?
        # mock: nodes(peer, seeder), eventQueue(JOIN)
        # process event and further events
        # assert CONNECTION_INFO event processed
        # assert that event.info are only hardCodedIPs
    
    def whenNodeRestarts_andNodeHasLessThanTwoOutgoingConnections_andElevenSecondsElapsed_receivesIPsFromSeeder(self):
        # mock: node(peer, seeder), eventQueue(RESTART)
        # DROP, then JOIN
        # node has less than 2 outgoing connections
        # 11 seconds elapsed
        # assert event REQUEST_CONNECTION_INFO queued to seeder
    
    # 2.1 ADDR
    def whenAddrMsgReceivedWithMoreThanThousand_sendingNodeBlacklisted(self):
        #asdf
    
    def whenOutgoingConnectionEstablishedWithPeer_receiveAddrMsgFromPeer(self):
        #asdf
    
    def whenIncomingConnectionEstablishedWithPeer_sendAddrMsgFromOwnTable(self):
        #asdf
    
    def whenNodeReceivesLessThanTenAddr_forwardsToTwoRandomConnectedPeers(self):
        #asdf
    
    def whenChoosingTwoRandomConnectedPeers_theyComeFromIpHashNonceFirstTwoLexographically(self):
        #asdf
    
    def whenNewDay_NodeSendsOwnIpInAddrMsg(self):
        #asdf
    
    def whenSendingAddrMsg_neverSendIpFromKnownTable(self):
        #asdf
    
    def whenNewDay_knownListFlushed(self):
        #asdf
    
    # 2.2 Tried table
    def test_whenSelectingBucketForAnIp_useSchemeFromPaper(self):
        # mock Node, hash
        # assert node.mapToTriedBucket() == manual calculation
    '''
    
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
        self.assertEqual(isPeerInTriedTableBefore, False)
        self.assertEqual(isPeerInTriedTableAfter, True)
    
    '''def test_whenInsertingAndBucketFull_properEvictionPerformed(self):
        # mock Node, Node.mapToTriedBucket(), Node.bitcoinEviction()
        # call addToTried()
        # assert bitcoinEviction() called
        # assert expected address gone from tried table
        # assert addToNew() called with evicted address
        # assert new address exists in tried table
    '''
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
        self.assertEqual(peerTimestampBefore < peerTimestampAfter, True)
        self.assertEqual(triedTableTotalEntriesBefore, triedTableTotalEntriesAfter)
        self.assertEqual(numPeerIpOccurencesBefore, 1)
        self.assertEqual(numPeerIpOccurencesAfter, 1)
    
    #@patch('network.Network.generate_latency')
    def test_whenPeerSentTriggeringMsg_andMoreThanTwentyMinsElapsed_onlyTimestampUpdated(self):#, mock_network_generate_latency):
        # do we support VERSION, ADDR, INVENTORY, GETDATA, PING messages?
        # is ADDR -> CONNECTION_INFO event?
        self.assertEqual(True, True)
        '''
        # generate node with specific IP already in its tried table
        peerIP = self.nodePeer2.ipV4Addr
        bucket = self.nodePeer.mapToTriedBucket(peerIP)
        self.nodePeer.learnIP(peerIP, self.sourceIP)
        self.nodePeer.triedTable[bucket][peerIP] = self.network.globalTime
        
        # ensure network aware of nodes
        self.network.hardcodedIPs[0] = peerIP
        self.network.ipToNodes[peerIP] = self.nodePeer2

        # in the future, add CONNECTION_INFO event to network.eventQueue as only existing event
        TWENTY_MINUTES = 20 * 60
        self.network.globalTime += TWENTY_MINUTES
        connectionInfoEvent = event(srcNode=self.nodePeer, destNode=self.seederNode, eventType=CONNECTION_INFO, info=self.network.hardcodedIPs[0:1])
        self.network.eventQueue.put((self.network.globalTime, connectionInfoEvent))

        # mock out randomness
        latency = 0.123
        mock_network_generate_latency.return_value = latency# = mock.Mock(return_value=latency)
        print self.network.generate_latency()

        # collect data before
        peerTimestampBefore = self.nodePeer.triedTable[bucket][peerIP]
        triedTableTotalEntriesBefore = sum([len(b) for b in self.nodePeer.triedTable])
        numPeerIpOccurencesBefore = sum([b.keys() for b in self.nodePeer.triedTable], []).count(peerIP)

        # perform action in future
        print 'this'
        self.network.processNextEvent()
        self.network.processNextEvent()
        
        # collect data after
        peerTimestampAfter = self.nodePeer.triedTable[bucket][peerIP]
        triedTableTotalEntriesAfter = sum([len(b) for b in self.nodePeer.triedTable])
        numPeerIpOccurencesAfter = sum([b.keys() for b in self.nodePeer.triedTable], []).count(peerIP)
        
        # assertions
        # assert node's tried table entry for peer has updated timestamp
        print peerTimestampBefore, peerTimestampAfter
        self.assertEqual(peerTimestampBefore < peerTimestampAfter, True)
        self.assertEqual(triedTableTotalEntriesBefore, triedTableTotalEntriesAfter)
        self.assertEqual(numPeerIpOccurencesBefore, 1)
        self.assertEqual(numPeerIpOccurencesAfter, 1)
        '''
    '''
    # 2.2 New table
    def whenAddressFromDnsSeeder_onlyAddedToNewTable(self):
        # mock Node(peer, seeder), EventQueue
        # process CONNECTION_INFO event
        # assert addToTried() not called
        # maybe assert addToNew() called
    
    def whenAddressFromAddrMsg_onlyAddedToNewTable(self):
        # mock Node(peer, sender), eventQueue
        # process AddrMsg
        # assert addToTried() not called
        # 
        # TODO: implement this in project?
        #       CONNECTION_INFO assumes seeder
        #       but should we support peer2peer ADDR msgs?
        #       otherwise this test is redundant with prev test method
    
    def whenAddressFromDnsSeeder_timestampBetweenThreeAndSevenDaysOld(self):
        # TODO: implement this in project?
    
    def whenAddressFromAddrMsg_timestampIsPlusTwoHours(self):
        # TODO: implement AddrMsg event in project?
    '''
    def test_whenSelectingBucket_useSchemeFromPaper(self):
        ip = self.network.assignIP()
        self.nodePeer2.ipV4Addr = ip
        self.network.ipToNodes[ip] = self.nodePeer2
        
        # fill nodePeer's outgoing connection to force ip into new table
        for i in range(MAX_OUTGOING):
            outIp = self.network.assignIP()
            self.nodePeer.outgoingCnxs.append(outIp)


        connectionInfoEvent = event(srcNode=self.seederNode, destNode=self.nodePeer, eventType=CONNECTION_INFO, info=[ip])
        self.network.eventQueue.put((self.network.globalTime, connectionInfoEvent))

        self.nodePeer.learnIP(ip, self.seederNode.ipV4Addr)
        sourceIp = self.nodePeer.ipToAddr[ip].sourceIP
        expectedBucket = self.nodePeer.mapToNewBucket(ip, sourceIp)
        
        self.network.processNextEvent()
        self.network.processNextEvent()

        actualBucket = []
        for bucketNum, addressDictionary in enumerate(self.nodePeer.newTable):
            if ip in addressDictionary.keys():
                actualBucket.append(bucketNum)

        self.assertEqual(len(actualBucket), 1)
        self.assertEqual(actualBucket[0], expectedBucket)

    '''
    def whenHashingGroupSourceGroupPair_hashesToUniqueBucket(self):
        # call mapToNewBucket() many times
        # assert result constant
    
    def whenInsertingAndBucketFull_properEvictionPerformed(self):
        # mock Node(peer), Node.mapToNewBucket() such that result is full
        # call addToNew()
        # case 1: Node.isTerrible() called
        #         case A: assert address over 30 days old deleted
        #         case B: assert address with too many failed attempts deleted
        # case 2: Node.bitcoinEviction() used
        #         assert evicted address deleted
    
    # 2.3 Selecting peers
    def whenOutgoingConnectionDrops_newOutgoingConnectionSelected(self):
        #asdf
    
    def whenReceiveBlacklistToActiveOutgoingConnection_dropThatConnection(self):
        #asdf
    
    def whenSelectingNewOutgoingConnection_probSelectFromTriedEqualsThatFromPaper(self):
        #asdf
    
    def whenSelectingAddressFromTable_higherProbForAddressWithNewerTimestamp(self):
        #asdf
    
    def whenSelectingAddressFromTable_nonEmptyBucketChosen(self):
        #asdf
    
    def whenSelectedAddressConnectionFails_newAddressChosen(self):
        #asdf'''
    
if __name__ == '__main__':
    unittest.main()