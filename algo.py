import networkx as nx
from pq import MyPQ

class SortedEdgeScoreList():
    """
        to get edge by rank, use Ld.edges[rank]
        to get demand by rank, use Ld.demands[rank]
        to get demand by edge, use Ld.edge2d[edge]
    """
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


def get_candidate_edges(vrnet: nx.Graph, sn: int):
    """
        input: virtual network, transit network, seeding number
        return:
        - Ld (SortedEdgeScoreList) with length limit of sn
    """
    # it is assumed that if an edge represents, it means the two node are close within distance of tau
    edge_score_list = [] # unsorted list
    for u, v, attr in vrnet.edges(data=True):
        edge_score_tuple = ((u, v), attr['weight'])
        edge_score_list.append(edge_score_tuple)

    return SortedEdgeScoreList(edge_score_list, sn)


def find_tfvrpath(tfvrnet: nx.Graph, sn: int, itmax: int):
    """
        input: transformed virtual network, seeding number, iteration max
        return: found path
    """

    ######## VARIABLE INITIALIZATION

    pq = MyPQ(order='descending')   # priority queue
    dt = dict()                     # domination table
    k = tfvrnet.number_of_nodes()+1 # maximum number of node in final path
    ld = None                       # list of edges sorted in descending order base on their demand 
    dmax = 0                        # largest possible demand value
    mu = list()                     # best path so far, is a list of nodes
    omax = 0                        # objective value of mu
    it = 0                          # iteration counter

    print(f'max path length (K): {k}')

    ######## Expansion-based Traversal Algorithm (ETA)

    #### initialization phase

    ld = get_candidate_edges(tfvrnet, sn)
    k = min(len(ld), k)

    # calculate dmax
    dmax = sum(ld.demands[:k])

    # because no connectivity involved, Omax == Odmax
    omax = ld.demands[0] / dmax
    mu = [*ld.edges[0]] # tuple unpacking

    # push path seeds into Q
    for i, e in enumerate(ld.edges):
        if i < k:
            cursor = k - 1
            dub = 1 # ub = upper bound
        else:
            cursor = k - 2
            dub = (dmax - ld.demands[k - 1] + ld.edge2d[e]) / dmax
        pq.push(dub, [*e], ld.edge2d[e] / dmax, cursor)

    #### expansion phase

    while pq:
        ocpub, cp, ocp, cur = pq.pop()
        # print(it, 'pop:', ocpub, cp, ocp, cur)
        if ocpub < omax or (it >= itmax or itmax == -1):
        # if it >= itmax or itmax == -1:
            # print("break", ocpub, Omax, cur, it)
            break
        it += 1

        # expansion from two ends with best neighbors
        result = []
        for end_node in [cp[0], cp[-1]]:
            e = None
            maxd_e = float('-inf')
            for v in tfvrnet.neighbors(end_node):
                if (end_node, v) in ld.edge2d and v not in cp:
                    # p = e + cp
                    # O(p) = Od(p)/dmax = (Od(e) + Od(cp))/dmax = Ld[e]/dmax + O(cp)
                    d_op = ld.edge2d[(end_node, v)]
                    if d_op > maxd_e:
                        e, maxd_e = v, d_op
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
            ocp = maxd_be / dmax + ocp
        else:
            ocp = (maxd_be + maxd_ee) / dmax + ocp

        if ocp > omax:
            omax, mu = ocp, cp
            # print('new mu', ocpub, cp, ocp, cur)
            # print('new mu', ocpub, len(cp), ocp, cur)

        # verification
        # the ocpub in the condition is not updated
        if ocpub > omax and len(cp) < k:
        # if len(cp) < K:

            # When a new edge is added, if its weight Ld[e] is smaller than the cur-th top edge's demand Ld(cur)
            # it means we can replace one top edge with the inserted one

            # have to compare the smaller one first, because if we compare the bigger one and
            # it happens to equal to Ld(curser), so no update, but than the smaller one update the curser
            # make the bigger one now smaller than Ld(curser), this will make wrong upper bound

            smaller, bigger = (maxd_be, maxd_ee) if maxd_be < maxd_ee else (maxd_ee, maxd_be) 

            if smaller < ld.demands[cur]:
                ocpub -= (ld.demands[cur] + smaller) / dmax
                cur -= 1
            if bigger < ld.demands[cur]:
                ocpub -= (ld.demands[cur] + bigger)  / dmax
                cur -= 1

            # domination checking and circle checking
            if ocp > dt.get(frozenset((be, ee)), 0) and be != ee:
                dt[frozenset((be, ee))] = ocp
                # print('push:', ocpub, cp, ocp, cur)
                # print('push:', ocpub, len(cp), ocp, cur)
                pq.push(ocpub, cp, ocp, cur)

    # print(f'findVirtualPath: {time()-time_begin} seconds')
    return mu
