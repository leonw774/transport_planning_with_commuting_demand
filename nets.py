import networkx as nx
import pandas as pd
# from geo import haversine
from math import sqrt

"""
    A node is a two-integer tuple
"""
def getRoadNetwork(path: str) -> nx.Graph:
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
    transit network equals road network
"""
def getTransitNetwork(road: nx.Graph):
    pass

"""
    Trajectory Data is unused.
    road edge demand is all 1
"""
def getTrajectoryData(path: str):
    pass


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