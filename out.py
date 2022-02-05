import networkx as nx
import matplotlib.pyplot as plt
from math import degrees
from geo import computeAngle

"""
    to be re-implemented
"""
def outputResult(mu: list, mu_tn:int,  Omax: float, roadNet: nx.Graph, transitNet: nx.Graph, trajData: list, output_path: str):
    
    # draw all roads
    # darker means more demands
    max_demand = max([attr.get('demand', 0) for u, v, attr in roadNet.edges(data=True)])
    for u, v, attr in roadNet.edges(data=True):
        d = max(min(1.0, attr.get('demand', 0) / max_demand), 0.05)
        color = (0.0, 0.0, 0.0, d)
        plt.plot(
            [roadNet.nodes[u]['x'], roadNet.nodes[v]['x']],
            [roadNet.nodes[u]['y'], roadNet.nodes[v]['y']],
            '-',
            color=color,
            lw=1)

    road_path = []
    for i in range(len(mu)-1):
        path = transitNet.edges[mu[i], mu[i+1]]['path']
        fromnodes = transitNet.nodes[mu[i]]['road']
        tonodes = transitNet.nodes[mu[i+1]]['road']
        if path[0] in fromnodes:
            road_path.extend(path)
        else:
            road_path.extend(reversed(path))

    # draw bus line
    prex = prey = None
    for i, n in enumerate(road_path):
        x, y = roadNet.nodes[n]['x'], roadNet.nodes[n]['y']
        if prex is not None:
            plt.plot([prex, x], [prey, y], '-r', lw=1)
        prex, prey = x, y

    # draw stops
    for n in transitNet.nodes():
        if n in mu:
            i = mu.index(n)
            if i >= 1 and i < len(mu) - 1:
                angle = computeAngle(
                    (transitNet.nodes[mu[i-1]]['x'], transitNet.nodes[mu[i-1]]['y']),
                    (transitNet.nodes[mu[i]]['x'], transitNet.nodes[mu[i]]['y']),
                    (transitNet.nodes[mu[i+1]]['x'], transitNet.nodes[mu[i+1]]['y']))
                angle = '\n' + str(round(degrees(angle), 1))
            else:
                angle = ''
            plt.plot(transitNet.nodes[n]['x'], transitNet.nodes[n]['y'], 'sb', markersize=2)
            plt.annotate(
                f'#{i}{angle}', 
                (transitNet.nodes[n]['x'], transitNet.nodes[n]['y']),
                fontsize=8)
        else:
            plt.plot(transitNet.nodes[n]['x'], transitNet.nodes[n]['y'], 'sg', markersize=2)
    
    plt.suptitle(f'number of turns: {mu_tn} \n transit path: {mu} \n Omax: {Omax}')
    plt.savefig(output_path+'.png')