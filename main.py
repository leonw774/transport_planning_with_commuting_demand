from algo import findTransformedVirtualPath
from argparse import ArgumentParser
from nets import getPhysical, getVirtual, makeTransformedVirtual
import networkx as nx
from out import outputImage, outputJSON

from io import StringIO
import cProfile
import pstats
from time import time

"""
    input: transformed virtual network, virtual network, physical network, found virtual path, source node
    return: virtual path, physical path, totalCost, totalLength
"""
def getPaths(tfvrNet: nx.Graph, vrNet: nx.Graph, phNet: nx.Graph, tfvrPath: list, source):
    # rotate tfvrPath so that it is a circle with the source as first element
    n = tfvrPath.index(source)
    if tfvrPath[0] == tfvrPath[-1]:
        # if vrPath is already a circle
        n = tfvrPath.index(source)
        tfvrPath = tfvrPath[n:-1] + tfvrPath[:n] + [source]
    else:
        tfvrPath = tfvrPath[n:] + tfvrPath[:n] + [source]
    
    vrPath = [tfvrPath[0]]
    for i in range(len(tfvrPath) - 1):
        vrSubPath = tfvrNet.edges[tfvrPath[i], tfvrPath[i+1]]['path']
        # print(f'vrSubPath[{i}]:, {vrSubPath}')
        if vrSubPath[-1] == vrPath[-1]:
            vrSubPath = list(reversed(vrSubPath))
        vrPath.extend(vrSubPath[1:])

    phPath = [vrNet.nodes[vrPath[0]]['phy']]
    for i in range(len(vrPath)-1):
        u, v = vrNet.nodes[vrPath[i]]['phy'], vrNet.nodes[vrPath[i+1]]['phy']
        if phNet.has_edge(u, v):
            phPath.append(v)
        else:
            try:
                sp = nx.dijkstra_path(phNet, u, v)
            except nx.NetworkXNoPath as e:
                print(f'getVirtualAndPhysicalPath: Can not find phyiscal path from {u} to {v}')
                raise e 
            phPath.extend(sp[1:])

    totalCost = sum(vrNet.edges[vrPath[n], vrPath[n+1]]['cost'] for n in range(len(vrPath) - 1))
    totalLength = sum(vrNet.edges[vrPath[n], vrPath[n+1]]['length'] for n in range(len(vrPath) - 1))
    return tfvrPath, vrPath, phPath, totalCost, totalLength


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--virtual-world-file', '-v',
                        dest='virtual_filepath',
                        required=True,
                        type=str
                        )
    parser.add_argument('--physical-world-file', '-p',
                        dest='physical_filepath',
                        required=True,
                        type=str
                        )
    parser.add_argument('--virtual-physical-mapping-file', '-m',
                        dest='vp_mapping_filepath',
                        required=True,
                        type=str
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
        print('Profiling...')
        pr = cProfile.Profile()
        pr.enable()

    print(f'virtual file:{args.virtual_filepath}')
    print(f'physical file:{args.physical_filepath}')
    
    ######## GET INPUT

    time_getnets = time()

    vrNet, source, destinations = getVirtual(args.virtual_filepath, args.vp_mapping_filepath)

    phNet, obstacles, phWorldL, phWorldW = getPhysical(args.physical_filepath)

    tfvrNet = makeTransformedVirtual(vrNet, source, destinations, args.alpha)

    print(f'virtual network has {vrNet.number_of_nodes()} nodes and {vrNet.number_of_edges()} edges')
    print(f'alpha: {args.alpha}, source: {source}, destination: {destinations}')
    print(f'physical network has {phNet.number_of_nodes()} nodes and {phNet.number_of_edges()} edges')
    print(f'transformed virtual network has {tfvrNet.number_of_nodes()} nodes and {tfvrNet.number_of_edges()} edges')

    print(f'read and make nets: {time()-time_getnets} seconds')

    print(f'physical path cost limit: {args.cost_limit}')
    print(f'algorithm parameter: itmax={args.vritmax} sn={args.sn}')

    time_findpaths = time()

    ######## FIND VIRTUAL PATH

    tfvrPath = findTransformedVirtualPath(tfvrNet, args.sn, args.vritmax)
    try:
        assert set(tfvrPath) == destinations | {source}
    except AssertionError as e:
        print('Error: tfvrPath does not contain all destinations or source. Missing:', (destinations | {source}) - set(tfvrPath))
        exit()

    ######## GET CORRESPONDING PHYSICAL PATH

    tfvrPath, vrPath, phPath, totalCost, totalLength = getPaths(tfvrNet, vrNet, phNet, tfvrPath, source)
    print(f'tfvrPath: {tfvrPath}')
    # print(f'vrPath: {vrPath}')
    # print(f'phPath: {phPath}')
    print(f'totalCost: {totalCost}, totalLength: {totalLength}')
    if args.cost_limit:
        if totalCost > args.cost_limit:
            print(f'Can not find path: total cost: {totalCost} is larger than cost limit: {args.cost_limit}')
            exit()
    
    print(f'find paths: {time()-time_findpaths} seconds')

    ######## OUTPUT

    if args.output:
        outputJSON(vrPath, totalCost, totalLength, vrNet, source, destinations, args)
        outputImage(vrPath, totalCost, totalLength, vrNet, source, destinations, phPath, phWorldL, phWorldW, obstacles, args)

    if args.use_profile:
        pr.disable()
        s = StringIO()
        pstats.Stats(pr, stream=s).strip_dirs().sort_stats('cumulative').print_stats()
        open('stat', 'w+', encoding='utf8').write(s.getvalue())
