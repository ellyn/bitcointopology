#!/usr/bin/env python2.7

import argparse
import pickle
import random
import networkx as nx
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument(
  '-f',
  '--filename',
  help='Filename from which to parse network state & generate graph (default: state.pickle)',
  default='state.pickle',
  type=str)
parser.add_argument(
  '-i',
  '--image',
  help='Filename to which to write graph visualization (default: graph.png)',
  default='graph.png',
  type=str)

args = parser.parse_args()

with open(args.filename, 'rb') as datafile:
  data = pickle.load(datafile)

graph = nx.Graph()

# TODO Add all nodes to graph, add connections appropriately. Example code below.

fakeNodes = range(100)
fakeEdges = [(random.randint(1, 100), random.randint(1, 100), random.randint(1, 10)) for _ in range(100)]

for node in fakeNodes:
  graph.add_node(node)

for edge in fakeEdges:
  graph.add_edge(edge[0], edge[1], weight = edge[2])

nx.draw(graph)
plt.savefig(args.image)
