from argparse import ArgumentParser 
import networkx as nx
from math import pi
import matplotlib.pyplot as plt
from pq import MyPQ
from geo import computeAngle
from nets import getRoadNetwork, getTransitNetwork, getTrajectoryData, SortedEdgeDemandList, findNeighbors

"""
input: road network, trajectory data
side effect:
- calculate and add 'demand' attribute to some of road network edges
"""
def computeDemand(roadNet: nx.Graph, trajData: list):
    for traj in trajData:
        nodelist = traj[1].split(" ")
        for i in range(len(nodelist)-1):
            e = roadNet.edges[nodelist[i], nodelist[i+1]]
            e['demand'] = e.get('demand', 0) + 1

"""
input: road network, transit network, seeding number
side effects:
- road_length_max: find and set to max
- calculate and add 'weighted_demand' attribute the roadNet edges that has 'demand'
reutrn:
- Ld (SortedEdgeDemandList) with length limit of sn
"""
def getCandidateEdges(roadNet: nx.Graph, transitNet: nx.Graph, sn: int):
    global road_length_max
    # find road_length_max
    for u, v in roadNet.edges():
        l = roadNet.edges[u, v]['length'] # because every thing in road network is stored as string
        if l > road_length_max:
            road_length_max = l

    # it is assumed that if an edge represents, it means the two node are close within distance of tau
    edge_demand_list = [] # unsorted list
    for u, v, attr in transitNet.edges(data=True):
        aggregated_weighted_demand = 0
        for i in range(len(attr['path'])-1):
            e = roadNet.edges[attr['path'][i], attr['path'][i+1]]
            if 'weighted_demand' in e:
                aggregated_weighted_demand += e['weighted_demand']
            elif 'demand' in e:
                # revised formula (2)
                e['weighted_demand'] = e['demand'] * (road_length_max - e['length']) * e['length']
                aggregated_weighted_demand += e['weighted_demand']

        edge_demand_tuple = ((u, v), aggregated_weighted_demand)
        edge_demand_list.append(edge_demand_tuple)

    return SortedEdgeDemandList(edge_demand_list, sn)

"""
to be re-implemented
"""
def outputResult(mu: list, mu_tn:int,  Omax: float, roadNet: nx.Graph, transitNet: nx.Graph, trajData: list, output_path: str):
    # draw all roads
    # darker means more demands
    
    max_demand = max([attr.get('demand', 0) for u, v, attr in roadNet.edges(data=True)])
    for u, v, attr in roadNet.edges(data=True):
        d = min(1.0, attr.get('demand', 0) / max_demand)
        color = (0.0, 0.0, 0.0, d)
        plt.plot(
            [roadNet.nodes[u]['x'], roadNet.nodes[v]['x']],
            [roadNet.nodes[u]['y'], roadNet.nodes[v]['y']],
            '-',
            color=color,
            lw=1)

    road_path = []
    for i in range(len(mu)-1):
        path = transitNet.edges[mu[i], mu[i+1]]['path']
        fromnodes = transitNet.nodes[mu[i]]['road']
        tonodes = transitNet.nodes[mu[i+1]]['road']
        if path[0] in fromnodes:
            road_path.extend(path)
        else:
            road_path.extend(reversed(path))

    # draw bus line
    prex = prey = None
    for i, n in enumerate(road_path):
        x, y = roadNet.nodes[n]['x'], roadNet.nodes[n]['y']
        if prex is not None:
            plt.plot([prex, x], [prey, y], '-r', lw=1)
        prex, prey = x, y

    # draw stops
    for n in transitNet.nodes():
        if n in mu:
            i = mu.index(n)
            if i >= 1 and i < len(mu) - 1:
                angle = computeAngle(
                    (transitNet.nodes[mu[i-1]]['x'], transitNet.nodes[mu[i-1]]['y']),
                    (transitNet.nodes[mu[i]]['x'], transitNet.nodes[mu[i]]['y']),
                    (transitNet.nodes[mu[i+1]]['x'], transitNet.nodes[mu[i+1]]['y']))
                angle = round(angle, 2)
            else:
                angle = ''
            plt.plot(transitNet.nodes[n]['x'], transitNet.nodes[n]['y'], 'sb', markersize=2)
            plt.annotate(
                f'#{i}\n{angle}', 
                (transitNet.nodes[n]['x'], transitNet.nodes[n]['y']),
                fontsize=8)
        else:
            plt.plot(transitNet.nodes[n]['x'], transitNet.nodes[n]['y'], 'sk', markersize=2)
    
    plt.suptitle(f'number of turns: {mu_tn} \n transit path: {mu} \n Omax: {Omax}')
    plt.savefig(output_path+'.png')

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
    # parser.add_argument('--transit-is-preprocessed',
    #                     dest='transit_is_preprocessed',
    #                     type=bool,
    #                     default=True
    #                     )
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
                        help='threshold for number of turns'
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
                        default='output'
                        )        
    args = parser.parse_args()
    
    ######## GET INPUT

    roadNet = getRoadNetwork(args.road_path)
    transitNet = getTransitNetwork(args.transit_path)
    trajData = getTrajectoryData(args.traj_path)

    ######## GLOBAL VARIABLE INITIALIZATION 

    Q = MyPQ()                          # priority queue
    DT = dict()                         # domination table
    K = transitNet.number_of_nodes()    # maximum number of node in final path
    Ld = None                           # list of edges sorted in descending order base on their demand 
    dmax = 0                            # largest possible demand value
    mu = list()                         # best path so far, is a list of nodes
    mu_tn = 0                           # number of turn that path mu has
    Omax = 0                            # objective value of mu
    it = 0                              # iteration counter
    itmax = args.itmax                  # limit of iteration
    tnmax = args.tnmax                  # threshold for number of turns
    road_length_max = 0                 # max road length in road network

    ######## PRE-PROCESS

    computeDemand(roadNet, trajData)

    # if args.transit_is_preprocessed is False:
    #     findNeighbors(transitNet, roadNet, args.tau)

    ######## Algorithm: ETA

    #### initialization phase

    Ld = getCandidateEdges(roadNet, transitNet, args.sn)
    K = min(len(Ld), K)

    # calculate dmax
    for i in range(K):
        dmax += Ld.demands[i]

    # because no connectivity involved, Omax == Odmax
    Omax = Ld.demands[0] / dmax
    mu = [*Ld.edges[0]]

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
            # I don't why but this happen
            continue
        
        # sometime you just can't find new edge?
        if be is not None:
            cp = [be] + cp
        if ee is not None:
            cp = cp + [ee]
        
        Ocp = (maxd_be + maxd_ee) / dmax + Ocp
        if Ocp > Omax:
            Omax = Ocp
            mu = cp
            # print('new mu:', cp, Ocp, tn, cur)
        
        # verification
        # the Ocpub in the condition is not updated
        if tn < tnmax and Ocpub > Omax and len(cp) < K:

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
                    tn = tnmax
            
            if ee is not None:
                ee_angle = computeAngle(
                    (transitNet.nodes[cp[-1]]['x'], transitNet.nodes[cp[-1]]['y']),
                    (transitNet.nodes[cp[-2]]['x'], transitNet.nodes[cp[-2]]['y']),
                    (transitNet.nodes[cp[-3]]['x'], transitNet.nodes[cp[-3]]['y']))
                # print(ee_angle)
                if ee_angle > pi/4:
                    tn += 1
                if ee_angle > pi/2:
                    tn = tnmax
            
            if Ocp == Omax:
                # if is mu
                mu_tn = tn
            
            # domination checking and circle checking
            if Ocp > DT.get(frozenset((be, ee)), 0) and be != ee:
                DT[frozenset((be, ee))] = Ocp
                # print('push:', Ocpub, cp, Ocp, tn, cur)
                Q.push(Ocpub, cp, Ocp, tn, cur)

    outputResult(mu, mu_tn, Omax, roadNet, transitNet, trajData, args.output_path)
