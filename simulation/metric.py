#!/usr/bin/env python

from matplotlib import pyplot as plt
import json, sys

metric = sys.argv[1]
data = json.loads(open('metrics.json').read())

x_axis = [x[0] for x in data]
y_axis = [x[1][metric] for x in data]

plt.plot(x_axis, y_axis)
