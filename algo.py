import networkx as nx
from pq import MyPQ

class SortedEdgeScoreList():
    """
        to get edge by rank, use Ld.edges[rank]
        to get demand by rank, use Ld.demands[rank]
        to get demand by edge, use Ld.edge2d[edge]
    """
    def __init__(self, unsorted_score_edge_list, sn: int) -> None:
        # list with descending demand value with limited length of sn
        # each element is a tuple (edge, demand)
        sortedlist = sorted(unsorted_score_edge_list, key=lambda x: x[1], reverse=True)[:sn]
        edge_tuple, demand_tuple = zip(*sortedlist)
        assert any(d >= 0 for d in demand_tuple) # please don't use negtive score
        self.edges = list(edge_tuple)
        self.demands = list(demand_tuple)
        self.edge2d = dict()
        # because edge is undirected, tuple order shouldn't matter
        # considered frozenset, but it has only has 2 element, so nah
        for (u, v), demand in sortedlist:
            self.edge2d[(u, v)] = demand
            self.edge2d[(v, u)] = demand

    def regularize(self, k: int) -> None:
        # to regularize the demand
        dmax = sum(self.demands[:k])
        # sometimes all demands are zero. the input counld just occassionally fucked up you know
        if dmax != 0:
            self.demands = [d / dmax for d in self.demands]
            self.edge2d = {key : value / dmax for key, value in self.edge2d.items()}

    def __len__(self):
        return len(self.edges)


def get_candidate_edges(vrnet: nx.Graph, sn: int):
    """
        input: virtual network, transit network, seeding number
        return:
        - Ld (SortedEdgeScoreList) with length limit of sn
    """
    # score = max_weight - weight
    max_weight = max(attr['weight'] for u, v, attr in vrnet.edges(data=True))
    # it is assumed that if an edge represents, it means the two node are close within distance of tau
    edge_score_list = [] # unsorted list
    for u, v, attr in vrnet.edges(data=True):
        edge_score_tuple = ((u, v), max_weight - attr['weight'])
        edge_score_list.append(edge_score_tuple)

    return SortedEdgeScoreList(edge_score_list, sn)


def find_tfvrpath(tfvrnet: nx.Graph, sn: int, itmax: int) -> list:
    """
        input: transformed virtual network, seeding number, iteration max
        return: found path
    """

    ######## VARIABLE INITIALIZATION

    pq = MyPQ(order='descending')   # priority queue
    dt = dict()                     # domination table
    k = tfvrnet.number_of_nodes()+1 # maximum number of node in final path, +1 because we allow circle
    ld = None                       # list of edges sorted in descending order base on their demand
    mu = list()                     # best path so far, is a list of nodes
    omax = 0                        # objective value of mu
    it = 0                          # iteration counter

    print(f'max path length (K): {k}')

    ######## Expansion-based Traversal Algorithm (ETA)

    #### initialization phase

    ld = get_candidate_edges(tfvrnet, sn)
    assert len(ld) >= k

    # regularization
    # ld.regularize(k)

    # because no connectivity involved, Omax == Odmax
    omax = ld.demands[0]
    mu = [*ld.edges[0]] # tuple unpacking

    # push path seeds into Q
    for i, e in enumerate(ld.edges):
        if i < k:
            cursor = k - 1
            d_ub = sum(ld.demands) # ub = upper bound
        else:
            cursor = k - 2
            d_ub = (sum(ld.demands) - ld.demands[k - 1] + ld.edge2d[e])
        pq.push(d_ub, [*e], ld.edge2d[e], cursor)

    #### expansion phase

    while pq:
        ocpub, cp, ocp, cur = pq.pop()
        # print(it, 'pop:', ocpub, cp, ocp, cur)
        if ocpub < omax or (it >= itmax or itmax == -1):
            # print("break", ocpub, Omax, cur, it)
            break
        it += 1

        # expansion from two ends with best neighbors
        result = []
        for end_node in [cp[0], cp[-1]]:
            e = None
            maxd_e = 0 # pray that negtive score will not happen
            second_highest_e = None
            second_highest_d_e = None
            for v in tfvrnet.neighbors(end_node):
                if (end_node, v) in ld.edge2d and v not in cp:
                    # p = e + cp
                    # O(p) = Od(p) = Od(e) + Od(cp) = Ld[e] + O(cp)
                    d_op = ld.edge2d[(end_node, v)]
                    if d_op > maxd_e:
                        second_highest_e, second_highest_d_e = e, maxd_e
                        e, maxd_e = v, d_op
            result.append((e, maxd_e, second_highest_e, second_highest_d_e))

        be, maxd_be, b_second_highest_e, b_second_highest_d_e = result[0]
        ee, maxd_ee, e_second_highest_e, e_second_highest_d_e = result[1]

        if be is None and ee is None:
            # yeah this happens. sometime it just can't find new edge?
            continue

        # be == ee is allowed to happen only when len(cp) >= k - 2
        # in other time, we use the edge with second highest score
        if be == ee:
            if len(cp) < k - 2:
                if b_second_highest_d_e >= e_second_highest_d_e:
                    be, maxd_be = b_second_highest_e, b_second_highest_d_e
                else:
                    ee, maxd_ee = e_second_highest_e, e_second_highest_d_e

        # print("be, maxd_be, ee, maxd_ee:", be, maxd_be, ee, maxd_ee)

        # update best path
        if be is not None:
            cp = [be] + cp
        if ee is not None:
            cp = cp + [ee]

        if be == ee:
            ocp = maxd_be + ocp
        else:
            ocp = maxd_be + maxd_ee + ocp

        if ocp > omax:
            omax, mu = ocp, cp
            # print('new mu', ocpub, cp, ocp, cur, 'omax', omax)
            # print('new mu', ocpub, len(cp), ocp, cur)

        # verification
        # the ocpub in the condition is not updated
        if ocpub > omax and len(cp) < k:

            # When a new edge is added, if its weight Ld[e] is smaller than the cur-th top edge's demand Ld(cur)
            # it means we can replace one top edge with the inserted one

            # have to compare the smaller one first, because if we compare the bigger one and
            # it happens to equal to Ld(curser), so no update, but than the smaller one update the curser
            # make the bigger one now smaller than Ld(curser), this will make wrong upper bound

            smaller, bigger = (maxd_be, maxd_ee) if maxd_be < maxd_ee else (maxd_ee, maxd_be)

            if smaller < ld.demands[cur]:
                ocpub -= (ld.demands[cur] - smaller)
                cur -= 1
            if bigger < ld.demands[cur]:
                ocpub -= (ld.demands[cur] - bigger)
                cur -= 1

            try:
                assert ocpub >= ocp
            except AssertionError as e:
                print('Ocpub < Ocp:', ocpub, cp, ocp, cur)
                raise e

            # domination checking and circle checking
            if ocp > dt.get(frozenset((be, ee)), 0):
                dt[frozenset((be, ee))] = ocp
                # print('push:', ocpub, cp, ocp, cur)
                # print('push:', ocpub, len(cp), ocp, cur)
                pq.push(ocpub, cp, ocp, cur)

    # print(f'findVirtualPath: {time()-time_begin} seconds')
    return mu
