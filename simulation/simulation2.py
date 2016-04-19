#!/usr/bin/env python2.7

import argparse, time, pickle, json

from constants import *
from network import Network
from node import Node

parser = argparse.ArgumentParser()
parser.add_argument(
  '-n',
  '--nodes',
  help='Run simulation with NODES number of nodes (default: 800)',
  default=800,
  type=int)
parser.add_argument(
  '-t',
  '--termination',
  help='Run simulation with TERMINATION termination condition (see constants.py)',
  default=TERMINATION_COND_TIME,
  type=int)
parser.add_argument(
  '-v',
  '--value',
  help='Run simulation with VALUE termination value (see constants.py)',
  default=86400,
  type=int)
parser.add_argument(
  '-l',
  '--latencyType',
  help='Use LATENCYTYPE type of latency (default: 0 - uniform)',
  default=UNIFORM,
  type=int)
parser.add_argument(
  '-d',
  '--darkNodeProb',
  help='Set dark node probability (fractional) to DARKNODEPROB (default: 0.5)',
  default=0.5,
  type=float)
parser.add_argument(
  '-f',
  '--filename',
  help='Filename to write final network state to at end of simulation',
  default='state.pickle',
  type=str)

metrics = {
  'diameter': lambda n: n.getLCCDiameter()
}

def executeSimulation(numNodes, latencyType, darkNodeProb, termCond, termVal, outFile):

  realStart = time.time()

  print('Simulation begun with {} nodes. Latency type: {}. Dark node probability: {}'.format(
    numNodes, latencyType, darkNodeProb))

  # Initialize network.
  network = Network(numInitNodes = NUM_INIT_NODES, totalNodes = numNodes, latencyInfo = latencyType, darkNodeProb = darkNodeProb)

  metric_log = []
  eventIndex = 0

  # Run simulation until time over.
  while not network.shouldTerminate(termCond, termVal):
    network.processNextEvent()
    # done every X events
    if eventIndex % METRIC_EVENT_INTERVAL == 0:
      metric_log.append((network.globalTime, {key: metrics[key](network) for key in metrics}))
    eventIndex += 1

  open('metrics.json', 'w').write(json.dumps(metric_log))
  
  realEnd = time.time()

  print('Simulation done in {} seconds. Writing out network state & initialization parameters to {}.'.format(realEnd - realStart, outFile))

  # Write out results.
  # TODO Add network state. Can't pickle dump the whole object (priority queue etc.). Presumably we need a node list & the event log.
  with open(outFile, 'wb') as outFile:
    pickle.dump({
      'randomSeed': randomSeed,
      'numNodes': numNodes, 
      'latencyType': latencyType,
      'darkNodeProb': darkNodeProb
    }, outFile)

  print('Network state written. Terminating.') 

if __name__ == '__main__':
  args = parser.parse_args()
  executeSimulation(args.nodes, args.latencyType, args.darkNodeProb, args.termination, args.value, args.filename)
