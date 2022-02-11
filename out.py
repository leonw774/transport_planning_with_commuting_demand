import networkx as nx
import matplotlib.pyplot as plt
from math import degrees
from geo import computeAngle

"""
    to be re-implemented
"""
def outputResult(mu: list, mu_tn:int,  Omax: float, roadNet: nx.Graph, output_path: str):
    plt.axis('off')

    # draw all roads
    # darker means bigger score
    max_score = max([attr.get('score', 0) for u, v, attr in roadNet.edges(data=True)])
    for u, v, attr in roadNet.edges(data=True):
        d = attr.get('score', 0) / max_score
        color = (0.0, 0.0, 0.0, d)
        plt.plot(
            [u[0], v[0]],
            [u[1], v[1]],
            '-',
            color=color,
            lw=1)

    # draw bus line
    prex = prey = None
    for i, n in enumerate(mu):
        x, y = n
        if prex is not None:
            plt.plot([prex, x], [prey, y], '-r', lw=1)
        prex, prey = x, y

    # draw stops
    for n in roadNet.nodes():
        if n in mu:
            i = mu.index(n)
            angle = ''

            # if i >= 1 and i < len(mu) - 1:
            #     angle = computeAngle(
            #         mu[i-1],
            #         mu[i],
            #         mu[i+1])
            #     angle = '\n' + str(round(degrees(angle), 1))
                
            plt.plot(n[0], n[1], 'sb', markersize=1)
            plt.annotate(
                f'#{i}{angle}', 
                n,
                color='r', 
                fontsize=8)
        else:
            plt.plot(n[0], n[1], 'sg', markersize=1)
    
    plt.figtext(
        0.5, 0.99,
        f'number of turns: {mu_tn} \n path: {mu} \n Omax: {Omax}',
        wrap=True,
        horizontalalignment='center',
        verticalalignment='top',
        fontsize=10)
    plt.savefig(output_path+'.png')