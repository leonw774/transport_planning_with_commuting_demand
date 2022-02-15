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
    return G.subgraph(largest_cc)

"""
    find the shortest path between the two road segments its two nodes represent on the road network.
    the path will include the beginning and ending road segment as it is a undirected graph
    the result will store in the attribute `path` of each edge as a list of road network edge id 
"""
""" def findShortestPath(road1: tuple, road2: tuple, roadNet: nx.Graph):
    # there are four combination of start and ending node between two undirected edge
    lengths = [
        nx.shortest_path_length(roadNet, road1[0], road2[0], weight='length'),
        nx.shortest_path_length(roadNet, road1[0], road2[1], weight='length'),
        nx.shortest_path_length(roadNet, road1[1], road2[0], weight='length'),
        nx.shortest_path_length(roadNet, road1[1], road2[1], weight='length')
    ]
    argmax_length = lengths.index(max(lengths))
    r1 = int(argmax_length >= 2)
    r2 = argmax_length % 2
    path = nx.shortest_path(roadNet, road1[r1], road2[r2], weight='length')
    # because path have to include the begin road and ending road
    # find other node on road
    r1_ = 0 if r1 else 1
    r2_ = 0 if r2 else 1
    # if this node is already in path then empty, otherwise get it
    r1__nid = '' if road1[r1_] in path else (road1[r1_] + ' ')
    r2__nid = '' if road1[r1_] in path else (' ' + road2[r2_])
    path_string = r1__nid + ' '.join(path) + r2__nid
    return path_string
"""

"""
    input: transit network, road network, tau
    side effect:
    - add edge between every node pair that their distance is less than or equal to tau
    - for each edge, find shortest path on road network, and add 'path' attribute to it
"""
""" def findNeighbors(transitNet: nx.Graph, roadNet: nx.Graph, tau: float):
    checked = set()
    for ni, attri in transitNet.nodes(data=True):
        for nj, attrj in transitNet.nodes(data=True):
            if frozenset([ni, nj]) in checked or ni == nj:
                continue
            checked.add(frozenset([ni, nj]))
            if haversine(attri['x'], attri['y'], attrj['x'], attrj['y']) < tau:
                pathstring = findShortestPath(transitNet.nodes[ni]['road'], transitNet.nodes[nj]['road'], roadNet)
                transitNet.add_edge(ni, nj, path=pathstring)
"""