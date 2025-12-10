# node.py
import asyncio
import math
import random
import time
from typing import Dict, Optional, Tuple, List, Set, Any

from messages import HelloMsg, DVMsg, SessionReq, SessionAck, DataMsg
from routing import Route, ensure_one_hop, apply_distance_vector


class DroneNode:
    def __init__(self, nid: int, channel: Any, cfg: Dict[str, Any],
                 world_size: Tuple[float, float]):
        self.nid = nid
        self.cfg = cfg
        self.channel = channel
        self.world_size = world_size

        x = random.uniform(0, world_size[0])
        y = random.uniform(0, world_size[1])
        self.pos: Tuple[float, float, float] = (x, y, 0.0)

        self._target_wp: Optional[Tuple[float, float, float]] = None
        self._wp_pause_until: float = 0.0
        self._speed = random.uniform(*cfg["speed_mps"])

        self.inbox: asyncio.Queue = asyncio.Queue()
        self.neighbors: Set[int] = set()
        # Track last time we heard from each neighbor (for aging)
        self.neighbor_last_seen: Dict[int, float] = {}

        # DV Routing table: dest -> Route(cost, next_hop, updated_at)
        self.rt: Dict[int, Route] = {self.nid: Route(0.0, self.nid, time.time())}

        # Sequence counters
        self._hello_seq = 0
        self._dv_seq = 0

        # Metrics (Data only)
        self.delivered: int = 0
        self.generated: int = 0
        self.latencies: List[float] = []
        self.hops_used: List[int] = []

        # Trace sink (assigned by viz)
        self._trace_sink = None

    # -------- Mobility --------

    def _pick_new_waypoint(self):
        tx = random.uniform(0, self.world_size[0])
        ty = random.uniform(0, self.world_size[1])
        tz = 0.0
        self._target_wp = (tx, ty, tz)
        self._speed = random.uniform(*self.cfg["speed_mps"])
        pause = random.uniform(*self.cfg["waypoint_pause_s"])
        self._wp_pause_until = time.time() + pause

    def _step_toward_waypoint(self, dt: float):
        if self._target_wp is None or time.time() < self._wp_pause_until:
            return
        tx, ty, tz = self._target_wp
        x, y, z = self.pos
        dx, dy = tx - x, ty - y
        dist = math.hypot(dx, dy)
        if dist < 1e-3:
            self._pick_new_waypoint()
            return
        step = self._speed * dt
        if step >= dist:
            self.pos = (tx, ty, tz)
            self._pick_new_waypoint()
        else:
            r = step / dist
            self.pos = (x + r * dx, y + r * dy, 0.0)

    async def mobility_task(self):
        self._pick_new_waypoint()
        tick = self.cfg["mobility_step_s"]
        while True:
            self._step_toward_waypoint(tick)
            await asyncio.sleep(tick)

    # -------- Neighbor Discovery & DV --------

    async def hello_task(self):
        period = self.cfg["hello_period_s"]
        while True:
            self._hello_seq += 1
            await self.channel.broadcast(self.nid, HelloMsg(self.nid, self.pos, self._hello_seq))
            await asyncio.sleep(period)

    async def dv_task(self):
        period = self.cfg["dv_period_s"]
        while True:
            self._dv_seq += 1
            vector = {dest: (route.cost, route.next_hop) for dest, route in self.rt.items()}
            await self.channel.broadcast(self.nid, DVMsg(self.nid, vector, self._dv_seq))
            await asyncio.sleep(period)

    async def neighbor_watch_task(self):
        """
        Periodically remove neighbors (and dependent routes) that have
        not been heard from for neighbor_timeout_s seconds.
        This makes DV routing react to mobility changes.
        """
        hello_period = self.cfg["hello_period_s"]
        timeout = self.cfg.get("neighbor_timeout_s", 3.0 * hello_period)
        check_period = timeout / 3.0

        while True:
            now = time.time()
            dead_neighbors = [
                nid for nid, last in list(self.neighbor_last_seen.items())
                if now - last > timeout
            ]

            if dead_neighbors:
                for nid in dead_neighbors:
                    self.neighbors.discard(nid)
                    self.neighbor_last_seen.pop(nid, None)

                # Remove direct 1-hop routes to dead neighbors
                for dead in dead_neighbors:
                    if dead in self.rt and self.rt[dead].next_hop == dead:
                        del self.rt[dead]

                # Remove any route whose next_hop is a dead neighbor
                for dest in list(self.rt.keys()):
                    if self.rt[dest].next_hop in dead_neighbors:
                        del self.rt[dest]

            await asyncio.sleep(check_period)

    # -------- Handshake: SessionReq / SessionAck --------

    async def app_task(self, all_ids: List[int]):
        """
        Application layer:
        - instead of sending DataMsg directly,
        - initiate a handshake with SessionReq.
        - DataMsg is only created after SessionAck reaches this node.
        """
        period = self.cfg["app_send_period_s"]
        while True:
            for _ in range(self.cfg["app_pairs_per_period"]):
                dst = random.choice(all_ids)
                if dst == self.nid:
                    continue
                # Only initiate if we currently have a route (approx "reachable")
                if dst not in self.rt:
                    continue
                session_id = random.randint(1, 10_000_000)
                req = SessionReq(
                    src=self.nid,
                    dst=dst,
                    session_id=session_id,
                    created_at=time.time(),
                    path=[self.nid],
                    hop_count=0,
                )
                await self._forward_session_req(req)
            await asyncio.sleep(period)

    async def _forward_session_req(self, msg: SessionReq):
        if not msg.path or msg.path[-1] != self.nid:
            msg.path.append(self.nid)

        if msg.dst == self.nid:
            # We are the target → create SessionAck
            ack = SessionAck(
                src=self.nid,
                dst=msg.src,
                session_id=msg.session_id,
                target=self.nid,
                created_at=time.time(),
                path=[self.nid],
                hop_count=0,
            )
            await self._forward_session_ack(ack)
            return

        route = self.rt.get(msg.dst)
        if route is None:
            return
        msg.hop_count += 1
        await self.channel.unicast(self.nid, route.next_hop, msg)

    async def _forward_session_ack(self, msg: SessionAck):
        if not msg.path or msg.path[-1] != self.nid:
            msg.path.append(self.nid)

        if msg.dst == self.nid:
            # Handshake complete at initiator → create DataMsg
            target = msg.target
            if target not in self.rt:
                return
            if hasattr(random, "randbytes"):
                payload = random.randbytes(self.cfg["data_payload_bytes"])
            else:
                payload = bytes(
                    [random.randint(0, 255) for _ in range(self.cfg["data_payload_bytes"])]
                )
            data = DataMsg(
                src=self.nid,
                dst=target,
                payload=payload,
                created_at=time.time(),
                path=[self.nid],
                hop_count=0,
            )
            self.generated += 1
            await self._forward_data(data)
            return

        route = self.rt.get(msg.dst)
        if route is None:
            return
        msg.hop_count += 1
        await self.channel.unicast(self.nid, route.next_hop, msg)

    # -------- Data Plane (after handshake) --------

    async def _forward_data(self, msg: DataMsg):
        if not msg.path or msg.path[-1] != self.nid:
            msg.path.append(self.nid)

        if msg.dst == self.nid:
            self.delivered += 1
            latency = time.time() - msg.created_at
            self.latencies.append(latency)
            self.hops_used.append(msg.hop_count)
            if self._trace_sink is not None:
                self._trace_sink(msg.path[:])
            return

        route = self.rt.get(msg.dst)
        if route is None:
            return
        msg.hop_count += 1
        await self.channel.unicast(self.nid, route.next_hop, msg)

    # -------- RX Loop --------

    async def rx_loop(self):
        while True:
            m = await self.inbox.get()
            if isinstance(m, HelloMsg):
                self.neighbors.add(m.src)
                self.neighbor_last_seen[m.src] = time.time()
                ensure_one_hop(self.rt, m.src, log=self.cfg["log_dv_changes"])

            elif isinstance(m, DVMsg):
                apply_distance_vector(self.rt, self.nid, m.src, m.vector, log=self.cfg["log_dv_changes"])

            elif isinstance(m, SessionReq):
                await self._forward_session_req(m)

            elif isinstance(m, SessionAck):
                await self._forward_session_ack(m)

            elif isinstance(m, DataMsg):
                await self._forward_data(m)

    # -------- Summary --------

    def summary(self) -> Dict[str, Any]:
        return {
            "nid": self.nid,
            "generated": self.generated,
            "delivered": self.delivered,
            "delivery_ratio": (self.delivered / self.generated) if self.generated else 0.0,
            "avg_latency_s": (sum(self.latencies) / len(self.latencies)) if self.latencies else None,
            "avg_hops": (sum(self.hops_used) / len(self.hops_used)) if self.hops_used else None,
            "neighbors_now": sorted(self.neighbors),
            "routes_now": {d: (r.next_hop, round(r.cost, 1)) for d, r in sorted(self.rt.items())},
        }
