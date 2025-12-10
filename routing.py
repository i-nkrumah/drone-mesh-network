from dataclasses import dataclass
from typing import Dict, Tuple
import time


@dataclass
class Route:
    cost: float
    next_hop: int
    updated_at: float


def ensure_one_hop(rt: Dict[int, Route], neighbor_id: int, *, log: bool = False):
    now = time.time()
    old = rt.get(neighbor_id)
    if old is None or old.cost > 1.0:
        rt[neighbor_id] = Route(cost=1.0, next_hop=neighbor_id, updated_at=now)
        if log:
            print(f"[DV] New 1-hop route to {neighbor_id}")


def apply_distance_vector(
    rt: Dict[int, Route],
    self_id: int,
    src: int,
    their_vector: Dict[int, Tuple[float, int]],
    *,
    log: bool = False,
):
    """Bellman-Ford relaxation: cost_via_src = 1 + their_cost."""
    ensure_one_hop(rt, src, log=log)
    now = time.time()
    for dest, (their_cost, _nh) in their_vector.items():
        if dest == self_id:
            continue
        cost_via_src = 1.0 + their_cost
        existing = rt.get(dest)
        if existing is None or cost_via_src + 1e-9 < existing.cost or existing.next_hop == src:
            rt[dest] = Route(cost=cost_via_src, next_hop=src, updated_at=now)
            if log:
                print(f"[DV] RT update: dest={dest} via {src}, cost={cost_via_src:.1f}")
