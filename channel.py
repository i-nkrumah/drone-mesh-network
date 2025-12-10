import asyncio
import math
import random
import time
from typing import Dict, Any, Optional


class WirelessChannel:
    """
    In-memory 'air' that delivers frames to nodes in range with delay/jitter.

    Simplified MAC (CSMA/CA-style):
    - channel_busy_until: when the medium becomes free.
    - medium_lock: ensures only one transmitter reserves the channel at a time.
    - Before each TX, nodes:
        * sense if channel is busy,
        * wait if needed,
        * apply random backoff,
        * then transmit.
    """

    def __init__(self, comm_range: float, cfg: Dict[str, Any]):
        self.comm_range = comm_range
        self.cfg = cfg
        self.nodes: Dict[int, Any] = {}

        # MAC state
        self.medium_lock = asyncio.Lock()
        self.channel_busy_until: float = 0.0

    def attach(self, node: Any):
        self.nodes[node.nid] = node

    # ---------- MAC core: CSMA/CA-like behavior ----------

    async def _wait_for_idle_and_backoff(self):
        """
        Wait until the channel appears idle, then perform random backoff.
        This is a simplified CSMA/CA without exponential window or RTS/CTS.
        """
        slot = self.cfg.get("mac_slot_s", 0.001)
        while True:
            now = time.time()
            if now >= self.channel_busy_until:
                # Channel looks idle → random backoff
                backoff = random.uniform(
                    self.cfg["mac_min_backoff_s"],
                    self.cfg["mac_max_backoff_s"],
                )
                await asyncio.sleep(backoff)
                # After backoff, check again
                if time.time() >= self.channel_busy_until:
                    return
            else:
                # Channel busy, wait a bit and sense again
                await asyncio.sleep(slot)

    async def _mac_send(self, sender_id: int, msg: Any, *, is_broadcast: bool, next_hop_id: Optional[int] = None):
        """
        CSMA/CA-style guarded send:
        - sense + backoff
        - reserve medium for mac_tx_duration_s
        - then perform original broadcast/unicast logic
        """
        while True:
            await self._wait_for_idle_and_backoff()
            async with self.medium_lock:
                now = time.time()
                if now < self.channel_busy_until:
                    # Lost the race; someone else reserved medium → retry
                    continue

                # Reserve medium for the TX duration
                tx_dur = self.cfg["mac_tx_duration_s"]
                self.channel_busy_until = now + tx_dur

                # Perform the actual wireless delivery (non-blocking on medium)
                if is_broadcast:
                    await self._raw_broadcast(sender_id, msg)
                else:
                    if next_hop_id is not None:
                        await self._raw_unicast(sender_id, next_hop_id, msg)
                return  # transmission done

    # ---------- Physical behaviors (now called from _mac_send) ----------

    async def _raw_broadcast(self, sender_id: int, msg: Any):
        sender = self.nodes[sender_id]
        sx, sy, sz = sender.pos
        tasks = []
        for nid, node in self.nodes.items():
            if nid == sender_id:
                continue
            dist = math.dist((sx, sy, sz), node.pos)
            if dist <= self.comm_range:
                jitter = random.uniform(*self.cfg["channel_jitter_s"])
                dist_delay = min(dist / self.cfg["prop_speed_mps"], self.cfg["max_per_hop_delay_s"])
                delay = self.cfg["channel_base_delay_s"] + jitter + dist_delay
                tasks.append(asyncio.create_task(self._deliver_with_delay(node, msg, delay)))
        if tasks:
            await asyncio.gather(*tasks)

    async def _raw_unicast(self, sender_id: int, next_hop_id: int, msg: Any):
        sender = self.nodes[sender_id]
        if next_hop_id not in self.nodes:
            return
        rx = self.nodes[next_hop_id]
        dist = math.dist(sender.pos, rx.pos)
        if dist > self.comm_range:
            return
        jitter = random.uniform(*self.cfg["channel_jitter_s"])
        dist_delay = min(dist / self.cfg["prop_speed_mps"], self.cfg["max_per_hop_delay_s"])
        delay = self.cfg["channel_base_delay_s"] + jitter + dist_delay
        await self._deliver_with_delay(rx, msg, delay)

    # ---------- Public API: broadcast/unicast with MAC ----------

    async def broadcast(self, sender_id: int, msg: Any):
        await self._mac_send(sender_id, msg, is_broadcast=True, next_hop_id=None)

    async def unicast(self, sender_id: int, next_hop_id: int, msg: Any):
        await self._mac_send(sender_id, msg, is_broadcast=False, next_hop_id=next_hop_id)

    async def _deliver_with_delay(self, node: Any, msg: Any, delay: float):
        await asyncio.sleep(delay)
        await node.inbox.put(msg)
