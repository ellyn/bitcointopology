#!/usr/bin/env python2.7

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
import json, sys

metric = sys.argv[1]
data = json.loads(open('metrics.json').read())

if metric == 'histogram':
  data = data[-1][1]['connectionDistribution']
  uniq = set(data)
  counts = [(u, len([x for x in data if x == u])) for u in uniq]
  counts = sorted(counts, key = lambda x:x[0])
  x_axis = [x[0] for x in counts]
  y_axis = [x[1] for x in counts]
  plt.ylim(min(y_axis) - 1, max(y_axis) + 1)
  plt.xlabel('Connection Count')
  plt.ylabel('Node Count')
  plt.bar(x_axis, y_axis)
  plt.show()
  
else:
  x_axis = [x[0] for x in data]
  try:
    y_axis = [x[1][metric] for x in data]
  except KeyError:
    print('Invalid metric! Options: {}.'.format(', '.join(data[0][1].keys())))
    sys.exit(1)

  plt.ylim(min(y_axis) - 1, max(y_axis) + 1)
  plt.plot(x_axis, y_axis, label = metric)
  plt.show()
