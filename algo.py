import networkx as nx
from pq import MyPQ

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
        edge_score_tuple = ((u, v), attr['weight'])
        edge_score_list.append(edge_score_tuple)

    return SortedEdgeScoreList(edge_score_list, sn)


"""
    input: transformed virtual network, seeding number, iteration max
    return: found path
"""
def findTransformedVirtualPath(tfvrNet: nx.Graph, sn: int, itmax: int):

    ######## VARIABLE INITIALIZATION 

    Q = MyPQ(order='descending')    # priority queue
    DT = dict()                     # domination table
    K = tfvrNet.number_of_nodes()+1 # maximum number of node in final path
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
        Q.push(dub, [*e], Ld.edge2d[e] / dmax, cursor)

    #### expansion phase

    while Q:
        Ocpub, cp, Ocp, cur = Q.pop()
        # print(it, 'pop:', Ocpub, cp, Ocp, cur)
        if Ocpub < Omax or (it >= itmax or itmax == -1):
        # if it >= itmax or itmax == -1:
            # print("break", Ocpub, Omax, cur, it)
            break
        it += 1

        # expansion from two ends with best neighbors
        result = []
        for end_node in [cp[0], cp[-1]]:
            e = None
            maxd_e = float('-inf')
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
        # print("be, maxd_be, ee, maxd_ee:", be, maxd_be, ee, maxd_ee)
        
        # update best path
        if be is None and ee is None:
            # print('yeah this happens. sometime it just can\'t find new edge?')
            continue
            
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
            # print('new mu', Ocpub, cp, Ocp, cur)
            # print('new mu', Ocpub, len(cp), Ocp, cur)
        
        # verification
        # the Ocpub in the condition is not updated
        if Ocpub > Omax and len(cp) < K:
        # if len(cp) < K:

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
                # print('push:', Ocpub, cp, Ocp, cur)
                # print('push:', Ocpub, len(cp), Ocp, cur)
                Q.push(Ocpub, cp, Ocp, cur)

    # print(f'findVirtualPath: {time()-time_begin} seconds')    
    return mu