from argparse import ArgumentParser 
import networkx as nx
from math import pi
from pq import MyPQ
from geo import computeAngle
from nets import getRoadNetwork, getTransitNetwork, getTrajectoryData
from out import outputResult

from io import StringIO
import cProfile
import pstats
from time import time

"""
    to get edge by rank, use Ld.edges[rank]
    to get demand by rank, use Ld.demands[rank]
    to get demand by edge, use Ld.edge2d[edge]
"""
class SortedEdgeScoreList():
    def __init__(self, unsorted_score_edge_list, sn) -> None:
        # list with descending demand value with limited length of sn
        # each element is a tuple (edge, demand)
        sortedlist = sorted(unsorted_score_edge_list, key=lambda x: x[1], reverse=True)[:sn]
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
    input: road network
    side effect:
    - calculate and add 'score' attribute to some of road network edges
"""
def computeScore(roadNet: nx.Graph):
    # find road_length_max
    road_length_max = max(roadNet.edges[u, v]['length'] for u, v in roadNet.edges())

    # find score
    for u, v in roadNet.edges():
        e = roadNet.edges[u, v]
        # revised formula (2)
        e['score'] = (road_length_max - e['length']) * e['length']
    
"""
    input: road network, transit network, seeding number
    reutrn:
    - Ld (SortedEdgeScoreList) with length limit of sn
"""
def getCandidateEdges(roadNet: nx.Graph, sn: int):
    # it is assumed that if an edge represents, it means the two node are close within distance of tau
    edge_score_list = [] # unsorted list
    for u, v, attr in roadNet.edges(data=True):
        edge_score_tuple = ((u, v), attr['score'])
        edge_score_list.append(edge_score_tuple)

    return SortedEdgeScoreList(edge_score_list, sn)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--input-path', '-i',
                        dest='input_path',
                        type=str
                        )
    # parser.add_argument('--transit-path',
    #                     dest='transit_path',
    #                     type=str,
    #                     default='data/transit.graphml'
    #                     )
    # parser.add_argument('--trajectory-path',
    #                     dest='traj_path',
    #                     type=str,
    #                     default='data/trajs.csv'
    #                     )
    # parser.add_argument('--tau',
    #                     dest='tau',
    #                     type=float,
    #                     default=500,
    #                     help='threshold for neighbor distance in meters. if transit is prepocessed, this does not matter.'
    #                     )
    parser.add_argument('--tnmax', '--turn-number-limit',
                        dest='tnmax',
                        type=int,
                        default=3,
                        help='threshold for number of turns, set -1 to be unlimited'
                        )
    parser.add_argument('--sn', '--seeding-number',
                        dest='sn',
                        type=int,
                        default=5000,
                        help='use top-sn edges in the list L_e as initial seeding path, set -1 to be unlimited'
                        )
    parser.add_argument('--itmax', '--iteration-limit',
                        dest='itmax',
                        type=int,
                        default=1000000,
                        help='limit of iteration, set -1 to be unlimited'
                        )
    parser.add_argument('--output', '-o',
                        dest='output',
                        action="store_true",
                        help='enable output'
                        )
    parser.add_argument('--profile', '-p',
                        dest='use_profile',
                        action="store_true",
                        help='enable profiling'
                        )
    args = parser.parse_args()

    print(f'input:{args.input_path}')

    if args.use_profile:
        pr = cProfile.Profile()
        pr.enable()
    time_begin = time()
    
    ######## GET INPUT

    roadNet = getRoadNetwork(args.input_path)
    # transitNet = getTransitNetwork(args.transit_path)
    # trajData = getTrajectoryData(args.traj_path)

    print(f'road network has {roadNet.number_of_nodes()} nodes and {roadNet.number_of_edges()} edges')

    ######## GLOBAL VARIABLE INITIALIZATION 

    Q = MyPQ()                                  # priority queue
    DT = dict()                                 # domination table
    K = roadNet.number_of_nodes()               # maximum number of node in final path
    Ld = None                                   # list of edges sorted in descending order base on their demand 
    dmax = 0                                    # largest possible demand value
    mu = list()                                 # best path so far, is a list of nodes
    mu_tn = 0                                   # number of turn that path mu has
    Omax = 0                                    # objective value of mu
    it = 0                                      # iteration counter
    itmax = args.itmax                          # limit of iteration
    Tn = args.tnmax if args.tnmax >= 0 else K   # threshold for number of turns

    ######## PRE-PROCESS

    computeScore(roadNet)

    print(f'K:{K} \nitmax:{itmax} \nTn:{Tn} \nsn:{args.sn}')

    ######## Expansion-based Traversal Algorithm (ETA)

    #### initialization phase

    Ld = getCandidateEdges(roadNet, args.sn)
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
        if Ocpub < Omax or (it >= itmax or itmax == -1):
            break
        it += 1

        # expansion from two ends with best neighbors

        result = []
        for end_node in [cp[0], cp[-1]]:
            e = None
            maxd_e = 0
            for v in roadNet.neighbors(end_node):
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
        
        # update turn number
        if be is not None:
            be_angle = computeAngle(
                cp[0],
                cp[1],
                cp[2])
            # print(be_angle)
            if be_angle > pi/4:
                tn += 1
            if be_angle > pi/2:
                tn = Tn
        
        if ee is not None:
            ee_angle = computeAngle(
                cp[-1],
                cp[-2],
                cp[-3])
            # print(ee_angle)
            if ee_angle > pi/4:
                tn += 1
            if ee_angle > pi/2:
                tn = Tn
        
        if Ocp == Omax: # is mu
            mu_tn = tn
        
        # verification
        # the Ocpub in the condition is not updated
        if (tn < Tn or Tn == -1) and Ocpub > Omax and len(cp) < K:

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
            
            # domination checking and circle checking
            if Ocp > DT.get(frozenset((be, ee)), 0) and be != ee:
                DT[frozenset((be, ee))] = Ocp
                # print('push:', Ocpub, cp, Ocp, tn, cur)
                Q.push(Ocpub, cp, Ocp, tn, cur)

    print(f'exec time: {time()-time_begin} seconds')

    if args.use_profile:
        pr.disable()
        s = StringIO()
        pstats.Stats(pr, stream=s).strip_dirs().sort_stats('cumulative').print_stats()
        open('stat', 'w+', encoding='utf8').write(s.getvalue())
        
    if args.output:
        outputResult(mu, mu_tn, Omax, roadNet, args)
