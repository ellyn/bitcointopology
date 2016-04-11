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
        self.nodePeer = Node(self.network.assignIP())
        self.nodePeer2 = Node(self.network.assignIP())

    # test method names must start with "test..."

    # Headers reference section from paper
    
    # 2
    def test_whenNodeReceivesIncomingConnectionRequest_doesNotExceedMaxIncomingConnections_andGeneratesConnectionFailureEvent(self):
        # generate node with max incoming connections
        sourceIP = self.network.assignIP()
        for ip in [self.network.assignIP() for i in range(MAX_INCOMING)]:
            self.nodePeer.incomingCnxs.append(ip)
            self.nodePeer.learnIP(ip, sourceIP)

        # communicating nodes have heard of each other before
        self.nodePeer.learnIP(self.nodePeer2.ipV4Addr, sourceIP)
        self.nodePeer2.learnIP(self.nodePeer.ipV4Addr, sourceIP)

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
        sourceIP = self.network.assignIP()
        for ip in [self.network.assignIP() for i in range(MAX_OUTGOING)]:
            self.nodePeer.outgoingCnxs.append(ip)
            self.nodePeer.learnIP(ip, sourceIP)

        # communicating nodes have heard of each other before
        self.nodePeer.learnIP(self.nodePeer2.ipV4Addr, sourceIP)
        self.nodePeer2.learnIP(self.nodePeer.ipV4Addr, sourceIP)

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
    
    def test_whenConnectSuccessToPeer_peerAddressInsertedIntoTried(self):
        # mock Node, eventQueue
        # processEvent(CONNECT)
        # assert addToTried() called
        # assert node IP exists in tried table (both ways)
    
    def test_whenInsertingAndBucketFull_properEvictionPerformed(self):
        # mock Node, Node.mapToTriedBucket(), Node.bitcoinEviction()
        # call addToTried()
        # assert bitcoinEviction() called
        # assert expected address gone from tried table
        # assert addToNew() called with evicted address
        # assert new address exists in tried table
    
    def test_whenInsertingAndPeerAddressAlreadyPresent_onlyTimestampUpdated(self):
        # mock Node(peerAddress already in table)
        # call addtoTried()
        # assert tried table size constant
        # assert peerAddress exists once
        # assert peerAddress timestamp newer
    
    def test_whenPeerSentTriggeringMsg_andMoreThanTwentyMinsElapsed_onlyTimestampUpdated(self):
        # do we support VERSION, ADDR, INVENTORY, GETDATA, PING messages?
        # is ADDR -> CONNECTION_INFO event?
        # 
        # mock Node(peerAddress in tried table w/timestamp more than 20 mins old), eventQueue
        # process CONNECTION_INFO event
        # assert node's tried table entry for peer has updated timestamp
    
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
    
    def whenSelectingBucket_useSchemeFromPaper(self):
        # mock Node(peer), hash
        # assert Node.mapToNewBucket() == manually calculated
    
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