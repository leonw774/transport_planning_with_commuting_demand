import networkx as nx
import pandas as pd
# from geo import haversine
from math import sqrt

def getPhysical(path: str) -> nx.Graph:
    with open(path, 'r', encoding='utf-8') as f:
        c = f.readlines()
    assert c[0] == 'obs\n'
    obs = set()
    i = 1
    while c[i] != 'pois\n':
        x, y = c[i].split()
        obs.add((int(x), int(y)))
        i += 1
    # now i point to 'pois'
    assert c[i+1] == 'length\n' and c[i+3] == 'width\n'
    length = int(c[i+2])
    width = int(c[i+4])

    # add all integer index coordinate as node except obs
    P = nx.Graph()
    P.add_nodes_from([ 
                (i, j)
            for j in range(width)
        for i in range(length)
        if (i, j) not in obs
    ])

    # find all neighbors:
    # for any grid, if you can go to another grid in chess queen moves, then that grid is a neighbor
    direction = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
    for ni in P.nodes():
        for d in direction:
            nj = ni[0] + d[0], ni[1] + d[1]
            while 0 <= nj[0] < length and 0 <= nj[1] < width and nj not in obs:
                P.add_edge(ni, nj)
                nj = nj[0] + d[0], nj[1] + d[1]

    return P, obs, length, width

"""
    A node is a two-integer tuple of (x, y)
"""
def getVirtual(path: str) -> nx.Graph:
    G = nx.Graph()
    with open(path, 'r', encoding='utf-8') as f:
        l = f.read().split('---\n')[1:]
    for e in l:
        n1, n2, v = e.split('\n')[:3]
        n1 = tuple(map(int, n1.split()))
        n2 = tuple(map(int, n2.split()))
        G.add_node(n1, x=n1[0], y=n1[1])
        G.add_node(n2, x=n2[0], y=n2[1])
        v = v.split()
        G.add_edge(n1, n2, length=sqrt(int(v[0]) ** 2 + int(v[1]) ** 2))
    
    # keep only the largest connected component
    largest_cc = max(nx.connected_components(G), key=len)
    G = G.subgraph(largest_cc)

    # compute score
    road_length_max = max(G.edges[u, v]['length'] for u, v in G.edges())
    for u, v in G.edges():
        e = G.edges[u, v]
        # revised formula (2)
        e['score'] = road_length_max - e['length']
        # e['score'] = (road_length_max - e['length']) * e['length']

    return G
