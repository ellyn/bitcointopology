import collections, random
from constants import *

# AddressInfo object maintains information about a known IP
addressInfo = collections.namedtuple('AddressInfo', ['nAttempts',
                                                     'sourceIP'])

class Node(object):
    def __init__(self, ipV4Addr, nodeType = PEER):
        self.nonce = random.randint(0, 65535)
        self.addrNonce = 0
        self.ipV4Addr = ipV4Addr
        self.nodeType = nodeType
        self.isOnline = False

        # A table is a list of buckets (dict) that map an IP (str) to a timestamp (float)
        self.triedTable = [{} for _ in range(NUM_TRIED_BUCKETS)]
        self.newTable = [{} for _ in range(NUM_NEW_BUCKETS)]

        # Connections are stored as lists of IP addresses (str)
        self.incomingCnxs = []
        self.outgoingCnxs = []

        # Dict mapping an IP address to its AddressInfo object
        # Only contains entries for IP addresses that the Node has learned
        self.ipToAddr = {}

        # Nodes we already sent/received ADDR messages today
        self.knownAddrIPs = []

        # Nodes can become blacklisted by sending a faulty ADDR message
        self.blacklistedIPs = []

        # For seeder nodes only: List of known IPs after crawling Bitcoin network
        if nodeType == SEEDER:
            self.knownIPs = []

    # Called when discovering an IP and creates an AddressInfo object for the IP
    # ip is the IP that was discovered
    # sourceIP is the IP from which Node learned ip
    def learnIP(self, ip, sourceIP):
        if ip not in self.ipToAddr:
            self.ipToAddr[ip] = addressInfo(nAttempts = 0, sourceIP = sourceIP)

    def incrementFailedAttempts(self, ip):
        if ip in self.ipToAddr:
            addrInfo = self.ipToAddr[ip]
            attempts = addrInfo.nAttempts
            self.ipToAddr[ip] = addrInfo._replace(nAttempts = attempts + 1)
        else:
            raise Exception('incrementFailedAttempts: No AddressInfo for given IP')

    # Returns the oldest IP of four randomly selected addresses in bucket
    # bucket is a dict mapping IP to timestamp 
    def bitcoinEviction(self, bucket):
        randomIPs = random.sample(bucket, 4)
        timestamps = map(lambda x : bucket[x], randomIPs)
        _, idx = min((_, idx) for (idx, _) in enumerate(timestamps))
        return randomIPs[idx]

    def mapToTriedBucket(self, ipAddr):
        temp = ipAddr.split('.')
        ipGroup = temp[0] + '.' + temp[1] # /16 group, i.e. first two numbers
        rand = str(self.nonce)
        ival = hash(rand + ipAddr) % 4
        ibkt = hash(rand + ipGroup + str(ival)) % 64
        return ibkt

    # Helper method: Removes the given IP from connections
    # Does not affect the Node's tables
    # Returns True if removal was successful, else False
    def removeFromConnections(self, ip):
        if ip in self.incomingCnxs:
            self.incomingCnxs.remove(ip)
        elif ip in self.outgoingCnxs:
            self.outgoingCnxs.remove(ip)
        else:
            return False
        return True

    def addToTried(self, ipAddr, globalTime, dtMin = 0):
        assert ipAddr in self.ipToAddr
        bucket = self.mapToTriedBucket(ipAddr)
        if ipAddr in self.triedTable[bucket]:
            # Only update if last message was > dtMin seconds ago.
            if globalTime - self.triedTable[bucket][ipAddr] >= dtMin:
                self.triedTable[bucket][ipAddr] = globalTime
        else:
            if len(self.triedTable[bucket]) == ADDRESSES_PER_BUCKET:
                # Get an IP via Bitcoin eviction, move to the new table,
                # and replace it with the new address
                oldestIP = self.bitcoinEviction(self.triedTable[bucket])

                del self.triedTable[bucket][oldestIP] 
                self.triedTable[bucket][ipAddr] = globalTime
                self.addToNew(oldestIP, globalTime)

                self.removeFromConnections(oldestIP)
            else:
                self.triedTable[bucket][ipAddr] = globalTime

    def mapToNewBucket(self, ipAddr, peerIP):
        ipTemp = ipAddr.split('.')
        ipGroup = ipTemp[0] + '.' + ipTemp[1]

        peerTemp = peerIP.split('.')
        srcIPGroup = peerTemp[0] + '.' + peerTemp[1] 

        rand = str(self.nonce)
        ival = hash(rand + ipGroup + srcIPGroup) % 32
        ibkt = hash(rand + srcIPGroup + str(ival)) % 256
        return ibkt

    # Returns terrible address from given bucket dictionary 
    # An address is terrible when it is more than 30 days old 
    # or has too many failed connection attempts
    def isTerrible(self, bucket, globalTime):
        for ip in bucket:
            if globalTime - bucket[ip] >= THIRTY_DAYS:
                return ip

            # Too many failed connection attempts
            if self.ipToAddr[ip].nAttempts >= MAX_RETRIES:
                return ip

        # If none are terrible, return an address via bitcoin eviction
        return self.bitcoinEviction(bucket)

    # Inserts ipAddr into the new table
    # peerIP is the source IP that ipAddr was learned from
    def addToNew(self, ipAddr, globalTime, peerIP = None):
        if peerIP == None:
            assert ipAddr in self.ipToAddr
            peerIP = self.ipToAddr[ipAddr].sourceIP
        bucket = self.mapToNewBucket(ipAddr, peerIP)
        if len(self.newTable[bucket]) == ADDRESSES_PER_BUCKET:
            terribleIP = self.isTerrible(self.newTable[bucket], globalTime)
            del self.newTable[bucket][terribleIP]
        self.newTable[bucket][ipAddr] = globalTime

    # Adds ip to list of incoming connections. Raises exception if dark matter node
    def addToIncomingCnxs(self, ip):
        if self.nodeType != DARK:
            self.incomingCnxs.append(ip)
        else:
            raise Exception("Trying to add incoming connection to dark matter node")

    # Adds ip to list of outgoing connections
    def addToOutgoingCnxs(self, ip):
        self.outgoingCnxs.append(ip)

    # For seeder nodes only: Updates its knowledge of the Bitcoin network
    def updateNetworkInfo(self, ipList):
        self.knownIPs = ipList

    # For seeder nodes only: Returns list of IP addresses as result of DNS query
    def getIPsForQuery(self):
        #print len(self.knownIPs)
        return random.sample(self.knownIPs, DNS_QUERY_SIZE)

    # Randomly select N IPs to send in an ADDR message, where N is randomly generated
    # Return list of chunked IPs, each sublist no greater than 1000
    def selectAddrs(self):
        totalTriedEntries = sum([len(b) for b in self.triedTable])
        totalNewEntries = sum([len(b) for b in self.newTable])
        totalAddresses = totalTriedEntries + totalNewEntries

        lowerBound = int(ADDR_LOWER_BOUND_PERCENT * totalAddresses) + 1
        upperBound = ADDR_UPPER_BOUND_NUM
        randomNum = random.randint(lowerBound, upperBound)

        flattenedIPs = []
        for bucket in self.triedTable:
            flattenedIPs.extend(bucket.keys())
        for bucket in self.newTable:
            flattenedIPs.extend(bucket.keys())

        numToSample = min(randomNum, len(flattenedIPs))
        ipList = random.sample(flattenedIPs, numToSample)

        return [ipList[i:i+MAX_ADDRS_PER_MSG] for i in range(0, len(ipList), MAX_ADDRS_PER_MSG)]

    def blacklistIP(self, ip):
        self.blacklistedIPs.append(ip)

    def isIpBlacklisted(self, ip):
        return (ip in self.blacklistedIPs)

    def addToKnownAddr(self, ip):
        self.knownAddrIPs.append(ip)

    # Randomly select [up to] 2 connected peers to send an ADDR message, as long as we haven't already done so today
    def selectPeersForAddrMsg(self, globalTime):
        # gather all connected peers into one dictionary{ip, hash}
        connectedPeersDict = {}
        for ip in self.incomingCnxs:
            if ip not in self.knownAddrIPs:
                connectedPeersDict[ip] = hash(str(self.addrNonce) + ip)
        for ip in self.outgoingCnxs:
            if ip not in self.knownAddrIPs:
                connectedPeersDict[ip] = hash(str(self.addrNonce) + ip)
        
        # take first two by hash lexographically
        firstTwoByHash = sorted(connectedPeersDict.items(), key=lambda x:x[1])[:2]
        twoIPs = [ip for (ip, h) in firstTwoByHash]

        self.knownAddrIPs.extend(twoIPs)

        return twoIPs

    # On a new day, flush ADDR recipient list, and change nonce
    def notifyNewDay(self, day):
        self.addrNonce = day
        self.knownAddrIPs = []
