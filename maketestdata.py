# import matplotlib.pyplot as plt
import networkx as nx
import osmnx
import pandas as pd
from random import choice, sample, random
from nets import haversine, getRoadNetwork, findNeighbors

def makeTestRoadNet(point, output_path):
    G = osmnx.graph_from_point(point, dist=1500, network_type='drive', retain_all=False)
    osmnx.plot_graph(G)
    G = osmnx.utils_graph.get_undirected(G)
    osmnx.io.save_graphml(G, output_path)
    # 先透過osmnx存成graphml，因為networkx的GraphML writer不支援<class 'shapely.geometry.linestring.LineString'>
    G = nx.read_graphml(output_path)
    # 然後才再用networkx轉成simple graph
    G = nx.Graph(G)
    nx.write_graphml(G, output_path)
    return getRoadNetwork(output_path)

# Make testing transit network graph
def makeTestTransitNet(roadNet, number, tau):
    # randomly find N edge as bus stop
    Gr = nx.Graph()
    generated_stops = set()
    i = 0
    edgelist = list(roadNet.edges())
    while len(generated_stops) < number:
        e = choice(edgelist)
        # calculate coordinate
        x0 = G.nodes[e[0]]['x']
        y0 = G.nodes[e[0]]['y']
        x1 = G.nodes[e[1]]['x']
        y1 = G.nodes[e[1]]['y']
        # random linear interpolation
        t = min(max(0.1, random()), 0.9)
        x = x0 * t + x1 * (1 - t)
        y = y0 * t + y1 * (1 - t)
        if len(generated_stops) > 0:
            if min([haversine(*gxy, x, y) for gxy in generated_stops]) < tau/3:
                continue
        generated_stops.add((x, y))
        Gr.add_node(i, road=e, x=x, y=y)
        i += 1
            

    # add edges and find shortest path between bus stops within distance tau
    findNeighbors(Gr, roadNet, tau)

    for n in Gr.nodes:
        Gr.nodes[n]['road'] = str(Gr.nodes[n]['road'])

    nx.write_graphml(Gr, 'data/transit.graphml')
    return Gr

# Make random trajectories by finding shortest path between two random nodes
def makeTestTrajectoryData(roadNet, number):
    trajs = {
        'id': list(range(number)),
        'trajectory' : []
    }
    nodesset = list(roadNet.nodes())
    id = 0
    while id < number:
        s, t = None, None
        while s == t:
            s = choice(nodesset)
            t = choice(nodesset)
        try:
            # use next() because we only want one 
            path = next(nx.shortest_simple_paths(roadNet, source=s, target=t, weight='length'))
        except:
            continue
        path_str = ' '.join(path)
        # print(f'id {id} \t s {s} \t t {t}')
        # print('added path: ' + path_str)
        trajs['trajectory'].append(path_str)
        id += 1

    trajsdf = pd.DataFrame(trajs)
    trajsdf.to_csv('data/trajs.csv', index=False)
    return trajs

if __name__ == "__main__":
    NS = 25          # number of bus stops
    NT = 100         # number of trajectories
    TAU = 500        # distance in meter
    print('tau =', TAU)
    G = makeTestRoadNet((25.0460, 121.5200), 'data/road.graphml')
    print(f'Road network has {G.number_of_edges()} edges')
    Gr = makeTestTransitNet(G, NS, TAU)
    print(f'Transit network has {Gr.number_of_nodes()} stops, {Gr.number_of_edges()} edges')
    D = makeTestTrajectoryData(G, NT)
    print(f'Generated {NT} trajectories with avg length of {sum([len(t) for t in D["trajectory"]])/len(D["trajectory"])}')

