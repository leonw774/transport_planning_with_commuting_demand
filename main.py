from argparse import ArgumentParser
from collections import deque
# from cost import redirected_walking_cost
from geo import computeAngle
from math import pi, atan2, dist
from nets import getPhysical, getVirtual
import networkx as nx
from out import outputResult
from pq import MyPQ

from io import StringIO
import cProfile
import pstats
from time import time

from ctypes import *

costlib = CDLL('./costlib.so')
costlib.redirected_walking_cost.restype = c_double

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
    input: virtual network, edges to block
    return: modified virtual network with blocked edges
"""
def blockEdges(vrNet: nx.Graph, blocked_edges: set):
    if blocked_edges:
        m_vrNet = vrNet.copy()
        # find score
        for u, v in m_vrNet.edges():
            e = m_vrNet.edges[u, v]
            if (u, v) in blocked_edges or (v, u) in blocked_edges:
                e['score'] = float('-inf')
        return m_vrNet
    else:
        return vrNet
    
"""
    input: virtual network, transit network, seeding number
    return:
    - Ld (SortedEdgeScoreList) with length limit of sn
"""
def getCandidateEdges(vrNet: nx.Graph, sn: int):
    # it is assumed that if an edge represents, it means the two node are close within distance of tau
    edge_score_list = [] # unsorted list
    for u, v, attr in vrNet.edges(data=True):
        edge_score_tuple = ((u, v), attr['score'])
        edge_score_list.append(edge_score_tuple)

    return SortedEdgeScoreList(edge_score_list, sn)

"""
    input: virtual network, turn-number max, seeding number, iteration max
    return: found path, objective value of found path 
"""
def findVirtualPath(vrNet: nx.Graph, tnmax: int, sn: int, itmax: int, blocked_edges: set):
    time_begin = time()
    
    ######## VARIABLE INITIALIZATION 

    Q = MyPQ(order='descending')    # priority queue
    DT = dict()                     # domination table
    K = vrNet.number_of_nodes()     # maximum number of node in final path
    Ld = None                       # list of edges sorted in descending order base on their demand 
    dmax = 0                        # largest possible demand value
    mu = list()                     # best path so far, is a list of nodes
    Omax = 0                        # objective value of mu
    it = 0                          # iteration counter
    Tn = tnmax if tnmax >= 0 else K # threshold for number of turns

    ######## Expansion-based Traversal Algorithm (ETA)

    #### initialization phase

    Ld = getCandidateEdges(vrNet, sn)
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
            for v in vrNet.neighbors(end_node):
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
def findPhysicalPath(phNet, vrPath):
    """
        Because the edges' cost are dependent of current path, we have to run
        single-source shortest path algorithm V times, where V is number of nodes/vertices
    """
    time_begin = time()

    found_path = None
    found_path_cost = float('inf')

    # there's two way to walk the virtual path
    for order in ['ascending', 'descending']:

        if order == 'descending':
            vrPath = list(reversed(vrPath))
        
        # pre-calculation
        # index 0 is all 0
        # index i is the value calculated with i and i-1

        # theta is ranged (-pi, pi], initial theta is 0
        vr_theta = [
            0 if i == 0 else
            atan2(vrPath[i][1] - vrPath[i-1][1], vrPath[i][0] - vrPath[i-1][0])  
            for i in range(len(vrPath))
        ]
        # length euclidean distance between two tuple, initial length is 0
        vr_length = [
            0 if i == 0 else dist(vrPath[i], vrPath[i-1])
            for i in range(len(vrPath))
        ]

        for n in phNet.nodes():
            # Dijkstra with dynamic edge weight and limited length
            # dynamic edge weight: the cost of an edge is denpendent to already walked path
            # limited length: the number of edges found in physical world sould be the same as the found virtual world path

            # initialize
            D = {v : (0 if v == n else float('inf')) for v in phNet.nodes()}
            Q = MyPQ()

            # current_cost, curent_physical_path, virtual_path_cursor, current_physical_theta
            Q.push(0, [n], 0, 0)
            
            while Q:
                Du, path, vp_cur, ph_theta = Q.pop()
                u = path[-1]
                for v in phNet.neighbors(u):
                    ph_steplength = dist(v, u)
                    ph_steptheta = atan2(v[1] - u[1], v[0] - u[0])
                    # vu_cost = redirected_walking_cost(vr_theta[vp_cur], ph_theta, vr_length[vp_cur+1], vr_theta[vp_cur+1], ph_steplength, ph_steptheta)
                    vu_cost = costlib.redirected_walking_cost(
                        c_double(vr_theta[vp_cur]),
                        c_double(ph_theta),
                        c_double(vr_length[vp_cur+1]),
                        c_double(vr_theta[vp_cur+1]),
                        c_double(ph_steplength),
                        c_double(ph_steptheta)
                    )
                    if D[v] > D[u] + vu_cost:
                        D[v] = D[u] + vu_cost
                        new_path = path + [v]
                        # if this path is already greater than currently found minimum cost, discard it
                        if D[v] < found_path_cost:
                            # if path will be the same length as vrPath after appending v, end search
                            if len(new_path) == len(vrPath): 
                                found_path, found_path_cost = new_path, D[v]
                                # print(f'found_path: {found_path} with cost: {found_path_cost}')
                            else:
                                Q.push(D[v], new_path, vp_cur+1, ph_steptheta)

    print(f'findPhysicalPath: {time()-time_begin} seconds')

    return found_path, found_path_cost

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--virtual-world-file', '-v',
                        dest='virtual_filepath',
                        type=str
                        )
    parser.add_argument('--physical-world-file', '-p',
                        dest='physical_filepath',
                        type=str
                        )
    parser.add_argument('--turn-number-max', '--tnmax', 
                        dest='tnmax',
                        type=int,
                        default=3,
                        help='threshold for number of turns, set -1 to be unlimited'
                        )
    parser.add_argument('--seeding-number', '--sn', 
                        dest='sn',
                        type=int,
                        default=5000,
                        help='use top-sn edges in the list L_e as initial seeding path, set -1 to be unlimited'
                        )
    parser.add_argument('--vr-iteration-max', '--vritmax', 
                        dest='vritmax',
                        type=int,
                        default=1000000,
                        help='limit of iteration, set -1 to be unlimited'
                        )
    parser.add_argument('--cost-limit', '-c',
                        dest='cost_limit',
                        type=int,
                        nargs='?',
                        help='limit of iteration, set -1 to be unlimited'
                        )
    parser.add_argument('--ph-traversal-level-max', '--phtrmax',
                        dest='phtrmax',
                        type=int,
                        default=4,
                        help='limit of iteration, set -1 to be unlimited'
                        )
    parser.add_argument('--output-filepath', '-o',
                        dest='output',
                        type=str,
                        nargs='?',
                        const='output/out',
                        help='enable output'
                        )
    parser.add_argument('--profile',
                        dest='use_profile',
                        action="store_true",
                        help='enable profiling'
                        )
    args = parser.parse_args()

    if args.use_profile:
        pr = cProfile.Profile()
        pr.enable()

    print(f'virtual file:{args.virtual_filepath}')
    print(f'pysical file:{args.physical_filepath}')
    
    ######## GET INPUT

    time_getnets = time()

    vrNet = getVirtual(args.virtual_filepath)

    phNet, obstacles, ph_world_length, ph_world_width = getPhysical(args.physical_filepath)

    print(f'virtual network has {vrNet.number_of_nodes()} nodes and {vrNet.number_of_edges()} edges')
    print(f'physical network has {phNet.number_of_nodes()} nodes and {phNet.number_of_edges()} edges')

    print(f'read and make nets: {time()-time_getnets} seconds')

    print(f'physical path cost limit: {args.cost_limit}')
    print(f'virtual - itmax:{args.vritmax} Tn:{args.tnmax} sn:{args.sn}')

    blocked_edges_queue = deque([set()]) # init a queue with an empty set
    blocked_edges_next_level_queue = deque()
    min_ph_path = None
    min_ph_path_cost = float('inf')
    ph_traverse_level_count = 0

    while blocked_edges_queue and ph_traverse_level_count < args.phtrmax:
        cur_blocked_edges = blocked_edges_queue.popleft()

        m_vrNet = blockEdges(vrNet, cur_blocked_edges)

        ######## FIND VIRTUAL PATH
        vr_path, vp_value = findVirtualPath(m_vrNet, args.tnmax, args.sn, args.vritmax, cur_blocked_edges)

        ######## FIND BEST PHYSICAL PATH
        ph_path, ph_path_cost = findPhysicalPath(phNet, vr_path)

        ######## Check cost
        if args.cost_limit is None:
            min_ph_path, min_ph_path_cost = ph_path, ph_path_cost
            break
        
        if args.cost_limit < ph_path_cost:
            # if this node didn't give ph_path_cost that is low enough
            # it branch leafs by adding more edges to be blocked
            for i in range(len(vr_path)-1):
                e = (vr_path[i], vr_path[i+1])
                new_blocked_edges = cur_blocked_edges.copy()
                new_blocked_edges.add(e)
                blocked_edges_next_level_queue.append(new_blocked_edges)
        elif ph_path_cost < min_ph_path_cost:
            min_ph_path, min_ph_path_cost = ph_path, ph_path_cost

        if len(blocked_edges_queue) == 0:
            # the level is all traversed
            # if a path is found then we can end
            if min_ph_path is not None:
                break
            else:
                blocked_edges_queue = blocked_edges_next_level_queue
                blocked_edges_next_level_queue = deque()
                ph_traverse_level_count += 1

    ######## OUTPUT

    if args.output:
        outputResult(vr_path, vp_value, vrNet, min_ph_path, min_ph_path_cost, ph_world_length, ph_world_width, obstacles, args)

    if args.use_profile:
        pr.disable()
        s = StringIO()
        pstats.Stats(pr, stream=s).strip_dirs().sort_stats('cumulative').print_stats()
        open('stat', 'w+', encoding='utf8').write(s.getvalue())
