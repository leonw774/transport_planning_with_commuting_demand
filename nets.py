import networkx as nx
import pandas as pd
from geo import haversine

"""
When read in from graphml file, every attribute is string, so have to convert
"""

def getRoadNetwork(path: str) -> nx.Graph:
    G = nx.read_graphml(path)
    for n in G.nodes:
        G.nodes[n]['x'] = float(G.nodes[n]['x'])
        G.nodes[n]['y'] = float(G.nodes[n]['y'])
    for eid in G.edges:
        G.edges[eid]['length'] = float(G.edges[eid]['length'])
    return G

def getTransitNetwork(path: str) -> nx.Graph:
    Gr = nx.read_graphml(path)
    for n in Gr.nodes:
        # try eval
        # eval can be evil, be careful
        evaled_road_attr = eval(Gr.nodes[n]['road'])
        if isinstance(evaled_road_attr, tuple) and len(evaled_road_attr) == 2:
            # node index of road network is string
            if isinstance(evaled_road_attr[0], str) and isinstance(evaled_road_attr[1], str):
                Gr.nodes[n]['road'] = evaled_road_attr
    
    for e in Gr.edges:
        Gr.edges[e]['path'] = Gr.edges[e]['path'].split(' ')

    return Gr

"""
Trajectory Data is a list of two-element lists: [[id1,  trajectory1], [id2,  trajectory2], ..., [idn,  trajectoryn]]
- id: int
- trajectory: string of road network node ids seperated by space
- road network node id: string composed of digits
"""
def getTrajectoryData(path: str) -> list:
    return pd.read_csv(path).to_dict('split')['data']

"""
to get edge by rank, use Ld.edges[rank]
to get demand by rank, use Ld.demands[rank]
to get demand by edge, use Ld.edge2d[edge]
"""
class SortedEdgeDemandList():
    def __init__(self, unsorted_demand_edge_list, sn) -> None:
        # list with descending demand value with limited length of sn
        # each element is a tuple (edge, demand)
        sortedlist = sorted(unsorted_demand_edge_list, key=lambda x: x[1], reverse=True)[:sn]
        edge_tuple, demand_tuple = zip(*sortedlist)
        self.edges = list(edge_tuple)
        self.demands = list(demand_tuple)
        self.edge2d = dict()
        # because edge is undirected, the tuple order shouldn't matter
        # considered frozenset, but it has only has 2 element, so nah
        for (u, v), demand in sortedlist:
            self.edge2d[(u, v)] = demand
            self.edge2d[(v, u)] = demand
    
    def __len__(self):
        return len(self.edges)

"""
    find the shortest path between the two road segments its two nodes represent on the road network.
    the path will include the beginning and ending road segment as it is a undirected graph
    the result will store in the attribute `path` of each edge as a list of road network edge id 
"""
def findshortestPath(road1: tuple, road2: tuple, roadNet: nx.Graph):
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
input: transit network, road network, tau
side effect:
- add edge between every node pair that their distance is less than or equal to tau
- for each edge, find shortest path on road network, and add 'path' attribute to it
"""
def findNeighbors(transitNet: nx.Graph, roadNet: nx.Graph, tau: float):
    checked = set()
    for ni, attri in transitNet.nodes(data=True):
        for nj, attrj in transitNet.nodes(data=True):
            if frozenset([ni, nj]) in checked or ni == nj:
                continue
            checked.add(frozenset([ni, nj]))
            if haversine(attri['x'], attri['y'], attrj['x'], attrj['y']) < tau:
                pathstring = findshortestPath(transitNet.nodes[ni]['road'], transitNet.nodes[nj]['road'], roadNet)
                transitNet.add_edge(ni, nj, path=pathstring)