from math import pi, radians, sin, cos, atan2, asin, acos, sqrt, dist

def haversine(lon1, lat1, lon2, lat2):
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371000 # Radius of earth in meters
    return c * r

"""
    input: 
    - latitude of point 1
    - latitude of point 2
    - longitude difference of point 1 and 2
    all angle are in radians
    output: initial bearing from point 1 to point 2, in [-PI, PI] range
"""
def bearing(lat1, lat2, dlong):
    y = sin(dlong) * cos(lat2)
    x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlong)
    theda = atan2(y, x)
    return theda

"""
    input: transit network and three transit network nodes, n1, n2, n3
    description:
    compute the angle between line n1->n2 and line n2->n3.
    the line of two nodes is a line that pass through the two nodes' geometrical location
    return: the angle in radian in [0, PI] range
"""
def computeAngle(point1, point2, point3) -> float:
    x1, y1 = point1
    x2, y2 = point2
    x3, y3 = point3
    # vector a
    xa, ya = x2 - x1, y2 - y1
    # vector b
    xb, yb = x3 - x2, y3 - y2
    # inner product ab
    iab = xa * xb + ya * yb
    theda = acos(iab / (dist(point2, point1) * dist(point3, point2)))
    return theda

"""
    Same as compute angle but on sphere
"""
def computeAngleSpherical(point1, point2, point3) -> float:
    x1, y1 = point1
    x2, y2 = point2
    x3, y3 = point3
    # compute initial bearing of (x1, y1) -> (x2, y2) and (x2, y2) -> (x3, y3)
    lat1, lat2, lat3, dlon12, dlon23 = map(radians, [y1, y2, y3, x2 - x1, x3 - x2])
    bearing12 = bearing(lat1, lat2, dlon12)
    bearing23 = bearing(lat2, lat3, dlon23)
    dbearing = abs(bearing23 - bearing12)
    if dbearing > pi: dbearing = 2*pi - dbearing
    return dbearing