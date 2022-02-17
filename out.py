import networkx as nx
import matplotlib.pyplot as plt
from math import degrees
from geo import computeAngle

"""
    to be re-implemented
"""
def outputResult(vr_path: list, vr_value: float, vrNet: nx.Graph, ph_path:list, ph_cost: float, ph_order: str, ph_world_length: int, ph_world_width: int, obs: list, args):

    plt.figure(figsize=(12, 6))

    plt.subplot(1, 2, 1)
    plt.axis('off')
    ######## DRAW VIRTUAL WORLD

    # draw all edges
    # darker means bigger score
    # max_score = max([attr.get('score', 0) for u, v, attr in vrNet.edges(data=True)])
    # for u, v, attr in vrNet.edges(data=True):
    #     d = attr.get('score', 0) / max_score
    #     color = (0.0, 0.0, 0.0, d)
    #     plt.plot(
    #         [u[0], v[0]],
    #         [u[1], v[1]],
    #         '-',
    #         color=color,
    #         lw=1)

    # draw path
    prex = prey = None
    for n in vr_path:
        x, y = n
        if prex is not None:
            plt.plot([prex, x], [prey, y], 'r-', lw=1)
        prex, prey = x, y

    # draw node
    for n in vrNet.nodes():
        if n not in vr_path:
            plt.plot(n[0], n[1], 'gs', markersize=1)
    
    # draw path node
    for i, n in enumerate(vr_path):
        angle = ''
        # if i >= 1 and i < len(vr_path) - 1:
        #     angle = computeAngle(
        #         vr_path[i-1],
        #         vr_path[i],
        #         vr_path[i+1])
        #     angle = '\n' + str(round(degrees(angle), 1))
        plt.plot(n[0], n[1], 'bs', markersize=1)
        plt.annotate(
            f'{i}{angle}', 
            n,
            color='k', 
            fontsize=8)
    
    plt.figtext(
        0.5, 0.99,
        f'virtual world: {args.virtual_filepath}\ntnmax: {args.tnmax} sn: {args.sn} itmax: {args.vritmax}\npath: {vr_path} Omax: {vr_value}',
        wrap=True,
        horizontalalignment='center',
        verticalalignment='top',
        fontsize=12)

    plt.subplot(1, 2, 2)
    plt.axis('off')
    ######## DRAW PHYSICAL WORLD

    # draw boundry
    plt.plot([-1, ph_world_length], [-1, -1], 'k-', lw=1)
    plt.plot([ph_world_length, ph_world_length], [-1, ph_world_width], 'k-', lw=1)
    plt.plot([-1, -1], [-1, ph_world_width], 'k-', lw=1)
    plt.plot([-1, ph_world_length], [ph_world_width, ph_world_width], 'k-', lw=1)

    # draw obs
    for i in range(ph_world_length):
        for j in range(ph_world_width):
            if (i, j) in obs:
                plt.plot(i, j, 'ks', markersize=4)
            else:
                plt.plot(i, j, 'gs', markersize=2)

    if ph_path is not None:
        # draw path
        prex = prey = None
        for i, n in enumerate(ph_path):
            x, y = n
            plt.annotate(
                str(i), 
                n,
                color='k', 
                fontsize=10)
            if prex is not None:
                plt.plot([prex, x], [prey, y], 'r-', lw=1)
            prex, prey = x, y

    plt.figtext(
        0.5, 0.1,
        f'physical world: {args.physical_filepath}\npath: {ph_path} order relative to virtual: {ph_order}\n cost: {ph_cost} cost limit: {args.cost_limit}',
        wrap=True,
        horizontalalignment='center',
        verticalalignment='top',
        fontsize=12)

    plt.savefig(f'{args.output}.png')