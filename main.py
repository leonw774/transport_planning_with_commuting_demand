from argparse import ArgumentParser 
import networkx as nx
from math import pi
import matplotlib.pyplot as plt
from pq import MyPQ
from geo import computeAngle
from nets import getRoadNetwork, getTransitNetwork, getTrajectoryData, findNeighbors
from out import outputResult

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
        # because edge is undirected, tuple order shouldn't matter
        # considered frozenset, but it has only has 2 element, so nah
        for (u, v), demand in sortedlist:
            self.edge2d[(u, v)] = demand
            self.edge2d[(v, u)] = demand
    
    def __len__(self):
        return len(self.edges)

"""
    input: road network, trajectory data
    side effect:
    - calculate and add 'demand', 'score' attribute to some of road network edges
"""
def computeDemand(roadNet: nx.Graph, trajData: list):
    # find road_length_max
    road_length_max = max(roadNet.edges[u, v]['length'] for u, v in roadNet.edges())
    
    # find demands
    for traj in trajData:
        nodelist = traj[1].split(" ")
        for i in range(len(nodelist)-1):
            e = roadNet.edges[nodelist[i], nodelist[i+1]]
            e['demand'] = e.get('demand', 0) + 1

    # find weighted demands
    for u, v in roadNet.edges():
        e = roadNet.edges[u, v]
        if 'demand' in e:
            # revised formula (2)
            e['score'] = e['demand'] * (road_length_max - e['length']) * e['length']
    
"""
    input: road network, transit network, seeding number
    side effects:
    - calculate and add attribute the roadNet edges that has 'demand'
    reutrn:
    - Ld (SortedEdgeDemandList) with length limit of sn
    - road_length_max
"""
def getCandidateEdges(roadNet: nx.Graph, transitNet: nx.Graph, sn: int):
    # it is assumed that if an edge represents, it means the two node are close within distance of tau
    edge_demand_list = [] # unsorted list
    for u, v, attr in transitNet.edges(data=True):
        aggregated_score = 0
        for i in range(len(attr['path'])-1):
            e = roadNet.edges[attr['path'][i], attr['path'][i+1]]
            aggregated_score += e.get('score', 0)

        edge_demand_tuple = ((u, v), aggregated_score)
        edge_demand_list.append(edge_demand_tuple)

    return SortedEdgeDemandList(edge_demand_list, sn)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--road-path',
                        dest='road_path',
                        type=str,
                        default='data/road.graphml'
                        )
    parser.add_argument('--transit-path',
                        dest='transit_path',
                        type=str,
                        default='data/transit.graphml'
                        )
    parser.add_argument('--trajectory-path',
                        dest='traj_path',
                        type=str,
                        default='data/trajs.csv'
                        )
    parser.add_argument('--tau',
                        dest='tau',
                        type=float,
                        default=500,
                        help='threshold for neighbor distance in meters. if transit is prepocessed, this does not matter.'
                        )
    parser.add_argument('--tn', '--turn-number',
                        dest='tnmax',
                        type=int,
                        default=3,
                        help='threshold for number of turns, set -1 to be unlimited'
                        )
    parser.add_argument('--sn', '--seeding-number',
                        dest='sn',
                        type=int,
                        default=5000,
                        help='\"we choose top-sn edges in the list L_e as initial seeding path\"'
                        )
    parser.add_argument('--itmax', '--iteration-limit',
                        dest='itmax',
                        type=int,
                        default=1000000,
                        help='limit of iteration'
                        )
    parser.add_argument('--output-path', '-o',
                        dest='output_path',
                        type=str,
                        default='output',
                        help='output file path. set to empty string (-o=\'\') to disable output'
                        )        
    args = parser.parse_args()
    
    ######## GET INPUT

    roadNet = getRoadNetwork(args.road_path)
    transitNet = getTransitNetwork(args.transit_path)
    trajData = getTrajectoryData(args.traj_path)

    ######## GLOBAL VARIABLE INITIALIZATION 

    Q = MyPQ()                                  # priority queue
    DT = dict()                                 # domination table
    K = transitNet.number_of_nodes()            # maximum number of node in final path
    Ld = None                                   # list of edges sorted in descending order base on their demand 
    dmax = 0                                    # largest possible demand value
    mu = list()                                 # best path so far, is a list of nodes
    mu_tn = 0                                   # number of turn that path mu has
    Omax = 0                                    # objective value of mu
    it = 0                                      # iteration counter
    itmax = args.itmax                          # limit of iteration
    Tn = args.tnmax if args.tnmax >= 0 else K   # threshold for number of turns

    ######## PRE-PROCESS

    computeDemand(roadNet, trajData)

    ######## Expansion-based Traversal Algorithm (ETA)

    #### initialization phase

    Ld = getCandidateEdges(roadNet, transitNet, args.sn)
    K = min(len(Ld), K)

    # calculate dmax
    dmax = sum(Ld.demands[:K])

    # because no connectivity involved, Omax == Odmax
    Omax = Ld.demands[0] / dmax
    mu = [*Ld.edges[0]] # tuple unpacking

    # push path seeds into Q
    for i, e in enumerate(Ld.edges):
        if i < K:
            cursor = K - 1
            dub = 1 # ub = upper bound
        else:
            cursor = K - 2
            dub = (dmax - Ld.demands[K - 1] + Ld.edge2d[e]) / dmax
        Q.push(dub, [*e], Ld.edge2d[e] / dmax, 0, cursor)

    #### expansion phase

    while Q:
        Ocpub, cp, Ocp, tn, cur = Q.pop()
        # print(it, 'pop:', Ocpub, cp, Ocp, tn, cur)
        if Ocpub < Omax or it >= itmax:
            break
        it += 1

        # expansion from two ends with best neighbors

        result = []
        for end_node in [cp[0], cp[-1]]:
            e = None
            maxd_e = 0
            for v in transitNet.neighbors(end_node):
                if (end_node, v) in Ld.edge2d and v not in cp:
                    # p = e + cp
                    # O(p) = Od(p)/dmax = (Od(e) + Od(cp))/dmax = Ld[e]/dmax + O(cp)
                    dOp = Ld.edge2d[(end_node, v)]
                    if dOp > maxd_e:
                        e, maxd_e = v, dOp
            result.append((e, maxd_e))
        
        be, maxd_be = result[0]
        ee, maxd_ee = result[1]
        
        # update best path

        if be is None and ee is None:
            continue
        # yeah this happens
        # sometime you just can't find new edge?
        if be is not None:
            cp = [be] + cp
        if ee is not None:
            cp = cp + [ee]

        # be == ee is allowed to happen
        # but it also means it can not be further expanded because it's now a circle 
        if be == ee:
            Ocp = maxd_be / dmax + Ocp
        else:
            Ocp = (maxd_be + maxd_ee) / dmax + Ocp

        if Ocp > Omax:
            Omax, mu = Ocp, cp
            #print('new mu', cp, Ocp, tn, cur)
        
        # verification
        # the Ocpub in the condition is not updated
        if tn < Tn and Ocpub > Omax and len(cp) < K:

            # When a new edge is added, if its weight Ld[e] is smaller than the cur-th top edge’s demand Ld(cur)
            # it means we can replace one top edge with the inserted one

            # have to compare the smaller one first, because if we compare the bigger one and
            # it happens to equal to Ld(curser), so no update, but than the smaller one update the curser
            # make the bigger one now smaller than Ld(curser), this will make wrong upper bound
            
            smaller, bigger = (maxd_be, maxd_ee) if maxd_be < maxd_ee else (maxd_ee, maxd_be) 

            if smaller < Ld.demands[cur]:
                Ocpub -= (Ld.demands[cur] + smaller) / dmax
                cur -= 1
            if bigger < Ld.demands[cur]:
                Ocpub -= (Ld.demands[cur] + bigger)  / dmax
                cur -= 1
            
            # update turn number
            if be is not None:
                be_angle = computeAngle(
                    (transitNet.nodes[cp[0]]['x'], transitNet.nodes[cp[0]]['y']),
                    (transitNet.nodes[cp[1]]['x'], transitNet.nodes[cp[1]]['y']),
                    (transitNet.nodes[cp[2]]['x'], transitNet.nodes[cp[2]]['y']))
                # print(be_angle)
                if be_angle > pi/4:
                    tn += 1
                if be_angle > pi/2:
                    tn = Tn
            
            if ee is not None:
                ee_angle = computeAngle(
                    (transitNet.nodes[cp[-1]]['x'], transitNet.nodes[cp[-1]]['y']),
                    (transitNet.nodes[cp[-2]]['x'], transitNet.nodes[cp[-2]]['y']),
                    (transitNet.nodes[cp[-3]]['x'], transitNet.nodes[cp[-3]]['y']))
                # print(ee_angle)
                if ee_angle > pi/4:
                    tn += 1
                if ee_angle > pi/2:
                    tn = Tn
            
            if Ocp == Omax: # is mu
                mu_tn = tn
            
            # domination checking and circle checking and turn-number checking
            if Ocp > DT.get(frozenset((be, ee)), 0) and be != ee:

                """
                    the order of updating mu and tn are weird
                    I think mu should be updated here and checked tn before it update
                    like this:
                """
                # if tn < Tn:
                #     if Ocp > Omax:
                #         Omax, mu, mu_tn = Ocp, cp, tn
                # else:
                #     continue

                DT[frozenset((be, ee))] = Ocp
                # print('push:', Ocpub, cp, Ocp, tn, cur)
                Q.push(Ocpub, cp, Ocp, tn, cur)

    if args.output_path:
        outputResult(mu, mu_tn, Omax, roadNet, transitNet, trajData, args.output_path)
