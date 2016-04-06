from constants import *

class Node(object):
    def __init__(self, ipV4Addr, nodeType = PEER):
        self.nonce = random.randint(0, 65535)
        self.ipV4Addr = ipV4Addr
        self.nodeType = nodeType
        self.triedTable = [{} for _ in range(NUM_TRIED_BUCKETS)]
        self.newTable = [{} for _ in range(NUM_NEW_BUCKETS)]
        self.incomingCnxs = []
        self.outgoingCnxs = []

    def mapToTriedBucket(self, ipAddr):
        temp = ipAddr.split('.')
        ipGroup = temp[0] + '.' + temp[1] # /16 group, i.e. first two numbers
        rand = str(self.nonce)
        ival = hash(rand + ipAddr) % 4
        ibkt = hash(rand + ipGroup + str(ival)) % 64
        return ibkt

    def addToTried(self, ipAddr, globalTime, dtMin = 0):
        bucket = self.mapToTriedBucket(ipAddr)
        if ipAddr in self.triedTable[bucket]:
            # Only update if last message was > dtMin seconds ago.
            if globalTime - self.triedTable[bucket][ipAddr] >= dtMin:
                self.triedTable[bucket][ipAddr] = dtMin
        else:
            if len(self.triedTable[bucket]) == 64:
                # Bitcoin eviction: remove four random addresses, replace oldest with new & put oldest in new table.
                indices = [random.randint(0, 63) for _ in range(4)]
                oldestIP, oldestTimestamp = None, globalTime
                IPs = self.triedTable[bucket].keys()
                for i in indices:
                    ip = IPs[i]
                    timestamp = self.triedTable[bucket][ip]
                    if timestamp < oldestTimestamp:
                        oldestIP, oldestTimestamp = ip, timestamp
                del self.triedTable[bucket][oldestIP] 
                self.triedTable[bucket][ipAddr] = globalTime
                self.addToNew(ipAddr, globalTime, oldVal)

                if oldestIP in self.incomingCnxs:
                    self.incomingCnxs.remove(oldestIP)
                elif oldestIP in self.outgoingCnxs:
                    self.outgoingCnxs.remove(oldestIP)
            else:
                self.triedTable[bucket][ipAddr] = globalTime

    def mapToNewBucket(self, ipAddr, peerIP):
        temp = ipAddr.split('.')
        ipGroup = temp[0] + '.' + temp[1]

        temp = peerIP.split('.')
        srcIPGroup = temp[0] + '.' + temp[1] 

        rand = str(self.nonce)
        ival = hash(rand + ipGroup + srcIPGroup) % 32
        ibkt = hash(rand + srcIPGroup + str(ival)) % 256
        return ibkt

    # Returns terrible address from given bucket dictionary 
    # An address is terrible when it is more than 30 days old 
    # or has too many failed connection attempts
    def isTerrible(self, bucket_dict):
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

    def addToNew(self, ipAddr, globalTime, peerIP):
        bucket = self.mapToNewBucket(ipAddr, peerIP)
        if len(self.newTable[bucket]) == 64:
            terribleIP = self.isTerrible(self.newTable[bucket])
            del self.newTable[bucket][terribleIP]
        self.newTable[bucket][ipAddr] = globalTime
