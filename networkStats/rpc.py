#!/usr/bin/env python2.7

'''

Steps to clone Bitcoin source tree & run daemon:

1. git clone https://github.com/bitcoin/bitcoin.git
2. cd bitcoin
3. ./autogen.sh
4. ./configure
5. make -j8
6. cd src
7. ./bitcoind -printtoconsole -rpcport=8888 -rpcallowip=127.0.0.1 -rpcuser=user -rpcpassword=pass

'''

import requests, json, re

#> Bitcoin JSON RPC (relevant: https://github.com/bitcoin/bitcoin/blob/master/src/rpc/net.cpp)

host = '127.0.0.1'
port = 8888
user = 'user'
pwd =  'pass'
url = 'http://{}:{}@{}:{}'.format(user, pwd, host, port)

run = lambda method, params: requests.post(url, data = json.dumps({'method': method, 'params': params, 'id': 0})).json()['result']

networkInfo = run('getnetworkinfo', [])
networkTotals = run('getnettotals', [])
addedNodeInfo = run('getaddednodeinfo', [True])
peerInfo = run('getpeerinfo', [])

#> IP Geolocation

def geolocate(addr):
  res = requests.get('http://ipinfo.io/{}/loc'.format(addr)).text
  res = res.split(',')
  return {'lat': float(res[0]), 'lon': float(res[1])}

#> Reverse DNS

'''
regex = re.compile('Top Level Domain: "<b>([^<]*)</b>"')

def reverseDNS(addr):
  res = requests.post('https://remote.12dt.com/lookup.php', data = {'ip': addr, 'Submit': 'Lookup'}).text
  print(res)
  mat = regex.findall(res)
  return mat[0][1]
'''

def reverseDNS(addr):
  res = requests.get('http://api.hackertarget.com/reversedns/?q={}'.format(addr)).text
  res = res.split(' ')[1]
  if res[-1] == '\n':
    res = res[:-1]
  return res

#> Stats

def makePeer(data):

  # IPv4 Address & Port
  addr = data['addr'].split(':')
  host = addr[0]
  port = int(addr[1])
  
  # Geolocate IP address if possible
  location = geolocate(host)

  # Reverse DNS (IP => Hostname)
  hostname = reverseDNS(host)   

  res = {
    'location': location,
    'host': host,
    'port': port,
    'hostname': hostname,
    'services': data['services'],
    'relayTX': data['relaytxes'],
    'lastSend': data['lastsend'],
    'lastRecv': data['lastrecv'],
    'bytesSent': data['bytessent'],
    'bytesRecv': data['bytesrecv'],
    'connTime': data['conntime'],
    'timeOffset': data['timeoffset'],
    'pingTime': data['pingtime'],
    'minPing': data['minping'],
    'pingWait': data['pingwait'] if 'pingwait' in data else None,
    'version': data['version'],
    'subVersion': data['subversion'] if 'subversion' in data else None,
    'inbound': data['inbound'],
    'startingHeight': data['startingheight'],
    'banScore': data['banscore'],
    'syncedHeaders': data['synced_headers'],
    'syncedBlocks': data['synced_blocks'],
    'bytesSentPerMsg': data['bytessent_per_msg'],
    'bytesRecvPerMsg': data['bytesrecv_per_msg']
  }
  return res

# e.g.

print(makePeer(peerInfo[0]))
