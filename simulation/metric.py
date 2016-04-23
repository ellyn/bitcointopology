#!/usr/bin/env python2.7

from matplotlib import pyplot as plt
import json, sys

metric = sys.argv[1]
data = json.loads(open('metrics.json').read())

x_axis = [x[0] for x in data]
try:
  y_axis = [x[1][metric] for x in data]
except KeyError:
  print('Invalid metric! Options: {}.'.format(', '.join(data[0][1].keys())))
  sys.exit(1)

plt.ylim(min(y_axis) - 1, max(y_axis) + 1)
plt.plot(x_axis, y_axis, label = metric)
plt.show()
