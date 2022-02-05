import heapq
from collections import namedtuple

"""
    (ub, path, o, tn, cur)
    ub: float. upper bound of objective value of path
    path: list of transit edges
    o: objective value of path
    tn: number of turns in path
    cur: cursor on the descending value list for upper bound calculation
"""

class MyPQ:
    def __init__(self) -> None:
        self.q = []

    def push(self, ub: float, path: list, o: float, tn: int, cur: int):
        # because heapq only do ascending order, have to push negtive ub
        heapq.heappush(self.q, (-ub, path, o, tn, cur))
    
    def pop(self):
        ub, p, o, tn, cur = heapq.heappop(self.q)
        return -ub, p, o, tn, cur
    
    def __len__(self):
        return len(self.q)