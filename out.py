import networkx as nx
import matplotlib.pyplot as plt
from math import degrees
from geo import computeAngle

"""
    to be re-implemented
"""
def outputResult(vr_path: list, vr_value: float, vrNet: nx.Graph, ph_path:list, ph_cost: float, ph_world_length: int, ph_world_width: int, obs: list, args):
    
    fig, (vrplt, phplt) = plt.subplots(1, 2)
    fig.axis('off')

    ######## DRAW VIRTUAL WORLD

    # draw all roads
    # darker means bigger score
    max_score = max([attr.get('score', 0) for u, v, attr in vrNet.edges(data=True)])
    for u, v, attr in vrNet.edges(data=True):
        d = attr.get('score', 0) / max_score
        color = (0.0, 0.0, 0.0, d)
        vrplt.plot(
            [u[0], v[0]],
            [u[1], v[1]],
            '-',
            color=color,
            lw=1)

    # draw path
    prex = prey = None
    for n in vr_path:
        x, y = n
        if prex is not None:
            vrplt.plot([prex, x], [prey, y], 'r-', lw=1)
        prex, prey = x, y

    # draw node
    for n in vrNet.nodes():
        if n not in vr_path:
            vrplt.plot(n[0], n[1], 'gs', markersize=1)
    
    # draw path node
    for i, n in enumerate(vr_path):
        angle = ''
        # if i >= 1 and i < len(vr_path) - 1:
        #     angle = computeAngle(
        #         vr_path[i-1],
        #         vr_path[i],
        #         vr_path[i+1])
        #     angle = '\n' + str(round(degrees(angle), 1))
        vrplt.plot(n[0], n[1], 'bs', markersize=1)
        vrplt.annotate(
            f'{i}{angle}', 
            n,
            color='r', 
            fontsize=8)
    
    vrplt.figtext(
        0.5, 0.99,
        f'virtual world: {args.virtual_filepath}\npath: {vr_path}\n Omax: {vr_value}',
        wrap=True,
        horizontalalignment='center',
        verticalalignment='top',
        fontsize=10)

    ######## DRAW PHYSICAL WORLD

    # draw boundry
    phplt.plot([0, ph_world_length], [0, 0], 'k-', lw=1)
    phplt.plot([ph_world_length, ph_world_length], [0, ph_world_width], 'k-', lw=1)
    phplt.plot([0, 0], [0, ph_world_width], 'k-', lw=1)
    phplt.plot([0, ph_world_length], [ph_world_width, ph_world_width], 'k-', lw=1)

    # draw obs
    for o in obs:
        phplt.plot(o[0], o[1], 'rs', markersize=2)

    # draw path
    prex = prey = None
    for n in ph_path:
        x, y = n
        if prex is not None:
            phplt.plot([prex, x], [prey, y], 'r-', lw=1)
        prex, prey = x, y

    phplt.figtext(
        0.5, 0.99,
        f'physical world: {args.physical_filepath}\npath: {ph_path}\n cost: {ph_cost}',
        wrap=True,
        horizontalalignment='center',
        verticalalignment='top',
        fontsize=10)

    fig.savefig(f'out_tnmax={args.tnmax}_sn={args.sn}_itmax={args.itmax}.png')