from argparse import ArgumentParser
from collections import deque
from cost import costFunc
from geo import computeAngle
from math import pi, atan2, dist
from nets import getPhysical, getVirtual, makeTransformedVirtual
import networkx as nx
from out import outputResult
from pq import MyPQ

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
    input: transformed virtual network, turn-number max, seeding number, iteration max
    return: found path, objective value of found path
"""
def findTransformedVirtualPath(tfvrNet: nx.Graph, Tn: int, sn: int, itmax: int) -> tuple[list, float]:

    ######## VARIABLE INITIALIZATION 

    Q = MyPQ(order='descending')    # priority queue
    DT = dict()                     # domination table
    K = tfvrNet.number_of_nodes()   # maximum number of node in final path
    Ld = None                       # list of edges sorted in descending order base on their demand 
    dmax = 0                        # largest possible demand value
    mu = list()                     # best path so far, is a list of nodes
    Omax = 0                        # objective value of mu
    it = 0                          # iteration counter

    print(f'K: {K}')

    ######## Expansion-based Traversal Algorithm (ETA)

    #### initialization phase

    Ld = getCandidateEdges(tfvrNet, sn)
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
        # if it >= itmax or itmax == -1:
            print("break", Ocpub, Omax, cur, it)
            break
        it += 1

        # expansion from two ends with best neighbors

        result = []
        for end_node in [cp[0], cp[-1]]:
            e = None
            maxd_e = 0
            for v in tfvrNet.neighbors(end_node):
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
            # yeah this happens
            continue
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
            # print('new mu', Ocpub, cp, Ocp, tn, cur)
            # print('new mu', Ocpub, len(cp), Ocp, tn, cur)
        
        if Tn > 0:
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
        # if (tn < Tn or Tn == -1) and len(cp) < K:

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
                # print('push:', Ocpub, len(cp), Ocp, tn, cur)
                Q.push(Ocpub, cp, Ocp, tn, cur)

    # print(f'findVirtualPath: {time()-time_begin} seconds')    
    return mu, Omax


"""
    input: transformed virtual network, virtual network, physical network, found virtual path
    return: physical path
"""
def getVirtualAndPhysicalPath(tfvrNet: nx.Graph, vrNet: nx.Graph, tfvrPath: list) -> tuple[list, list]:
    vrPath = [tfvrPath[0]]
    for i in range(len(tfvrPath) - 1):
        vrPath.extend(tfvrNet.edges[tfvrPath[i], tfvrPath[i+1]]['path'][1:])
    phPath = [vrNet.nodes[n]['phy'] for n in vrPath]
    return vrPath, phPath

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
                        default=-1,
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
                        type=float,
                        nargs='?',
                        help='limit of iteration, set -1 to be unlimited'
                        )
    parser.add_argument('--alpha', '-a',
                        dest='alpha',
                        type=float,
                        default=1.0,
                        help='alpha for transformed virtual network edge weight'
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

    vrNet, source, destinations = getVirtual(args.virtual_filepath)

    phNet, obstacles, phWorldL, phWorldW = getPhysical(args.physical_filepath)

    tfvrNet = makeTransformedVirtual(vrNet, source, destinations, args.alpha, costFunc)

    print(f'virtual network has {vrNet.number_of_nodes()} nodes and {vrNet.number_of_edges()} edges')
    print(f'source: {source}, destination: {destinations}')
    print(f'physical network has {phNet.number_of_nodes()} nodes and {phNet.number_of_edges()} edges')
    print(f'transformed virtual network has {phNet.number_of_nodes()} nodes and {phNet.number_of_edges()} edges')

    print(f'read and make nets: {time()-time_getnets} seconds')

    print(f'physical path cost limit: {args.cost_limit}')
    print(f'algorithm parameter: itmax={args.vritmax} Tn={args.tnmax} sn={args.sn}')

    time_findpaths = time()

    ######## FIND VIRTUAL PATH
    tfvrPath, tfvrValue = findTransformedVirtualPath(tfvrNet, args.tnmax, args.sn, args.vritmax)
    totalCost = -tfvrValue

    ######## GET CORRESPONDING PHYSICAL PATH
    vrPath, phPath = getVirtualAndPhysicalPath(tfvrNet, vrNet, tfvrPath)
    
    print(f'find paths: {time()-time_findpaths} seconds')

    ######## OUTPUT

    if args.output:
        outputResult(vrPath, totalCost, vrNet, phPath, phWorldL, phWorldW, obstacles, args)

    if args.use_profile:
        pr.disable()
        s = StringIO()
        pstats.Stats(pr, stream=s).strip_dirs().sort_stats('cumulative').print_stats()
        open('stat', 'w+', encoding='utf8').write(s.getvalue())
