#!/usr/bin/env python2.7

from constants import *
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
  '-n',
  '--nodes',
  help='Run simulation with NODES number of nodes (default: 800)',
  default=800,
  type=int)
parser.add_argument(
  '-l',
  '--length',
  help='Run simulation for LENGTH seconds (default: 86400)',
  default=86400,
  type=int)
parser.add_argument(
  '-t',
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


def executeSimulation(numNodes, simulationLength, latencyType, darkNodeProb):
  print('Simulation begun with {} nodes. Will run for {} seconds. Latency type: {}. Dark node probability: {}'.format(
    numNodes, simulationLength, latencyType, darkNodeProb))

if __name__ == '__main__':
  args = parser.parse_args()
  executeSimulation(args.nodes, args.length, args.latencyType, args.darkNodeProb)
