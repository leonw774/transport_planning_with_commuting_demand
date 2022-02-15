from argparse import ArgumentParser
from cost import redirected_walking_cost
from geo import computeAngle
from math import pi, atan2, dist
from nets import getPhysical, getVirtual
import networkx as nx
from out import outputResult
from pq import VRPQ, MyPQ

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
    input: virtual network
    side effect:
    - calculate and add 'score' attribute to edges
"""
def computeScore(virtualNet: nx.Graph):
    # find road_length_max
    road_length_max = max(virtualNet.edges[u, v]['length'] for u, v in virtualNet.edges())

    # find score
    for u, v in virtualNet.edges():
        e = virtualNet.edges[u, v]
        # revised formula (2)
        e['score'] = (road_length_max - e['length']) * e['length']
    
"""
    input: virtual network, transit network, seeding number
    return:
    - Ld (SortedEdgeScoreList) with length limit of sn
"""
def getCandidateEdges(virtualNet: nx.Graph, sn: int):
    # it is assumed that if an edge represents, it means the two node are close within distance of tau
    edge_score_list = [] # unsorted list
    for u, v, attr in virtualNet.edges(data=True):
        edge_score_tuple = ((u, v), attr['score'])
        edge_score_list.append(edge_score_tuple)

    return SortedEdgeScoreList(edge_score_list, sn)

"""
    input: virtual network, turn-number max, seeding number, iteration max
    return: found path, objective value of found path 
"""
def findVirtualPath(virtualNet, tnmax, sn, itmax):
    time_begin = time()
    
    ######## GLOBAL VARIABLE INITIALIZATION 

    Q = VRPQ()                          # priority queue
    DT = dict()                         # domination table
    K = virtualNet.number_of_nodes()    # maximum number of node in final path
    Ld = None                           # list of edges sorted in descending order base on their demand 
    dmax = 0                            # largest possible demand value
    mu = list()                         # best path so far, is a list of nodes
    Omax = 0                            # objective value of mu
    it = 0                              # iteration counter
    Tn = tnmax if tnmax >= 0 else K     # threshold for number of turns

    ######## PRE-PROCESS

    computeScore(virtualNet)

    print(f'K:{K} \nitmax:{itmax} \nTn:{Tn} \nsn:{sn}')

    ######## Expansion-based Traversal Algorithm (ETA)

    #### initialization phase

    Ld = getCandidateEdges(virtualNet, sn)
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
            for v in virtualNet.neighbors(end_node):
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
    
    print(f'findVirtualPath: {time()-time_begin} seconds')

    return mu, Omax

"""
    input: virtual network, physical network, found virtual path
    return: found physical path and its cost
"""
def findPhysicalPath(physicalNet, virtualPath):
    """
        Because the edges' cost are dependent of current path, we have to run
        single-source shortest path algorithm V times, where V is number of nodes/vertices
    """
    time_begin = time()

    found_path = None
    found_path_cost = float('inf')

    for n in physicalNet.nodes():
        # Dijkstra with dynamic edge weight and limited length
        # dynamic edge weight: the cost of an edge is denpendent to already walked path
        # limited length: the number of edges found in physical world sould be the same as the found virtual world path

        # initialize
        D = {v : (0 if v == n else float('inf')) for v in physicalNet.nodes()}
        visited = set()
        Q = MyPQ()

        # current_cost, curent_physical_path, virtual_path_cursor, current_physical_theta
        # theta is ranged (-pi, pi]
        Q.push(0, [n], 0, 0)
        
        while Q:
            du, path, vp_cur, ph_theta = Q.pop()
            u = path[-1]

            if u in visited:
                continue
            visited.add(u)

            if vp_cur == 0:
                vr_theta = 0
            else:
                vr_dir = virtualPath[vp_cur] - virtualPath[vp_cur-1]
                vr_theta = atan2(vr_dir[1], vr_dir[0])
            vr_steplength = dist(virtualPath[vp_cur], virtualPath[vp_cur+1])
            vr_stepdir = virtualPath[vp_cur+1] - virtualPath[vp_cur]
            vr_steptheta = atan2(vr_stepdir[1], vr_stepdir[0])

            for v in physicalNet.neighbors(u):
                ph_steplength = dist(v, u)
                ph_stepdir = v - u
                ph_steptheta = atan2(ph_stepdir[1], ph_stepdir[0])
                vu_cost = redirected_walking_cost(vr_theta, ph_theta, vr_steplength, vr_steptheta, ph_steplength, ph_steptheta)
                if D[v] > D[u] + vu_cost:
                    D[v] = D[u] + vu_cost

                    # if vp_cur will point to last element after plus 1, then the path is ended
                    if vp_cur == len(virtualPath) - 2: 
                        if D[v] < found_path_cost:
                            found_path = path + [v]
                            found_path_cost = D[v]
                    # if this path is already greater than currently found minimum cost then don't add it to queue
                    elif D[v] < found_path_cost:
                        Q.push(D[v], path + [v], vp_cur+1, ph_steptheta)

    print(f'found path: {found_path} with cost of {found_path_cost}')

    print(f'findPhysicalPath: {time()-time_begin} seconds')

    return found_path, found_path_cost

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--virtual-world-file', '-i',
                        dest='virtual_filepath',
                        type=str
                        )
    parser.add_argument('--physical-world-file', '-i',
                        dest='physical_filepath',
                        type=str
                        )
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

    if args.use_profile:
        pr = cProfile.Profile()
        pr.enable()

    print(f'input:{args.virtual_filepath}')
    
    ######## GET INPUT

    virtualNet = getVirtual(args.virtual_filepath)

    physicalNet, obstacles, ph_world_length, ph_world_width = getPhysical(args.physical_filepath)

    print(f'virtual network has {virtualNet.number_of_nodes()} nodes and {virtualNet.number_of_edges()} edges')
    print(f'physical network has {physicalNet.number_of_nodes()} nodes and {physicalNet.number_of_edges()} edges')

    ######## FIND VIRTUAL PATH

    vr_path, vr_path_value = findVirtualPath(virtualNet, args.tnmax, args.sn, args.itmax)

    ######## FIND BEST PHYSICAL PATH

    physical_path, ph_path_cost = findPhysicalPath(physicalNet, vr_path)

    ######## OUTPUT

    if args.output:
        outputResult(vr_path, vr_path_value, physical_path, ph_path_cost, virtualNet, ph_world_length, ph_world_width, obstacles, args)

    if args.use_profile:
        pr.disable()
        s = StringIO()
        pstats.Stats(pr, stream=s).strip_dirs().sort_stats('cumulative').print_stats()
        open('stat', 'w+', encoding='utf8').write(s.getvalue())
