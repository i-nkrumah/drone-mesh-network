# sim.py
import asyncio
from typing import Dict, Any, List

from config import SIM_CONFIG
from channel import WirelessChannel
from node import DroneNode


class Simulation:
    def __init__(self, cfg: Dict[str, Any] = SIM_CONFIG):
        self.cfg = cfg
        self.channel = WirelessChannel(cfg["comm_range"], cfg)
        self.nodes: List[DroneNode] = []
        self.tasks: List[asyncio.Task] = []
        self._running = False

    def build(self):
        W, H = self.cfg["world_size"]
        for nid in range(self.cfg["num_nodes"]):
            node = DroneNode(
                nid=nid,
                channel=self.channel,
                cfg=self.cfg,
                world_size=(W, H),
            )
            node._trace_sink = None  # will be set by viz
            self.channel.attach(node)
            self.nodes.append(node)

    async def run(self):
        self._running = True
        all_ids = [n.nid for n in self.nodes]
        for n in self.nodes:
            self.tasks.append(asyncio.create_task(n.mobility_task()))
            self.tasks.append(asyncio.create_task(n.hello_task()))
            self.tasks.append(asyncio.create_task(n.dv_task()))
            self.tasks.append(asyncio.create_task(n.rx_loop()))
            self.tasks.append(asyncio.create_task(n.app_task(all_ids)))
            self.tasks.append(asyncio.create_task(n.neighbor_watch_task()))
        await asyncio.sleep(self.cfg["sim_time_s"])
        for t in self.tasks:
            t.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self._running = False

    def report(self):
        tot_gen = sum(n.generated for n in self.nodes)
        tot_del = sum(n.delivered for n in self.nodes)
        all_lat = [lat for n in self.nodes for lat in n.latencies]
        all_hops = [h for n in self.nodes for h in n.hops_used]
        print("\n=== Simulation Summary ===")
        print(f"Nodes: {len(self.nodes)}  Range: {self.cfg['comm_range']} m  Duration: {self.cfg['sim_time_s']} s")
        print(f"Total generated (Data): {tot_gen}  Total delivered: {tot_del}")
        dr = (tot_del / tot_gen) if tot_gen else 0.0
        print(f"Delivery ratio: {dr:.3f}")
        if all_lat:
            print(f"Avg latency: {sum(all_lat)/len(all_lat):.4f} s")
        if all_hops:
            print(f"Avg hops: {sum(all_hops)/len(all_hops):.3f}")
