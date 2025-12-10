import asyncio
import math
import threading
import time
from collections import deque
from typing import List, Tuple, Dict, Optional, Any

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.collections import LineCollection
from matplotlib import cm, colors as mcolors
from matplotlib.widgets import Button

from config import SIM_CONFIG
from sim import Simulation


class PathTracer2D:
    """
    Keeps a fading buffer of route segments (x1,y1)-(x2,y2) for recently delivered DataMsg.
    Older segments fade out; buffer size and TTL are configurable.
    """

    def __init__(self, ttl_s: float, max_segments: int):
        self.ttl_s = ttl_s
        self.max_segments = max_segments
        self.buff: deque[Tuple[float, Tuple[float, float], Tuple[float, float]]] = deque()

    def add_path(self, nodes: List[Any], path_ids: List[int]):
        now = time.time()
        for i in range(len(path_ids) - 1):
            a = nodes[path_ids[i]].pos
            b = nodes[path_ids[i + 1]].pos
            self.buff.append((now, (a[0], a[1]), (b[0], b[1])))
            if len(self.buff) > self.max_segments:
                self.buff.popleft()

    def sweeper(self):
        """Remove expired segments."""
        now = time.time()
        while self.buff and (now - self.buff[0][0]) > self.ttl_s:
            self.buff.popleft()

    def segments_and_alphas(self):
        """Return segments and corresponding alphas based on age (0..1)."""
        now = time.time()
        segs = []
        alphas = []
        for ts, p1, p2 in self.buff:
            age = now - ts
            if age <= self.ttl_s:
                segs.append((p1, p2))
                # cosine fade: fresh=1.0 → old=0.0
                a = 0.5 * (1.0 + math.cos(math.pi * age / self.ttl_s))
                alphas.append(max(0.0, min(1.0, a)))
        return segs, alphas


class LiveArtist2D:
    def __init__(self, sim: Simulation):
        self.sim = sim
        self.links_visible = True
        self.paused = False
        self.anim = None  # strong ref to animation

        # We will visualize DV cost to this destination, changeable at runtime
        self.dv_dest = 0

        self.fig, self.ax = plt.subplots(figsize=(11, 7))
        W, H = self.sim.cfg["world_size"]
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(0, H)
        self.ax.set_aspect("equal", adjustable="box")
        self.ax.set_xlabel("X (m)")
        self.ax.set_ylabel("Y (m)")
        self.ax.set_title("Drone Mesh — DV Cost")

        # Node colors by ID (tab20)
        cmap_nodes = cm.get_cmap("tab20", self.sim.cfg["num_nodes"])
        self.node_colors = [cmap_nodes(i % cmap_nodes.N) for i in range(self.sim.cfg["num_nodes"])]

        # Initial scatter & labels
        xs = [n.pos[0] for n in self.sim.nodes]
        ys = [n.pos[1] for n in self.sim.nodes]
        self.scatter = self.ax.scatter(xs, ys, s=self.sim.cfg["node_size"], c=self.node_colors)
        off = self.sim.cfg["label_offset"]
        self.labels = [self.ax.text(n.pos[0], n.pos[1] + off, str(n.nid),
                                    ha="center", va="bottom", fontsize=10) for n in self.sim.nodes]

        # DV cost labels (numbers) under each node
        self.dv_labels = []
        dv_off = self.sim.cfg["label_offset"] + 14.0  # slightly further down
        for n in self.sim.nodes:
            txt = self.ax.text(
                n.pos[0],
                n.pos[1] - dv_off,
                "∞",  # initially unknown
                ha="center",
                va="top",
                fontsize=9,
                color="white",
            )
            self.dv_labels.append(txt)

        # Track DV cost changes for highlighting
        self.prev_costs: Dict[int, Optional[float]] = {n.nid: None for n in self.sim.nodes}
        self.dv_last_change_ts: Dict[int, float] = {n.nid: 0.0 for n in self.sim.nodes}
        self.dv_highlight_duration = 1.0  # seconds to keep label highlighted

        # Neighbor links with color by distance
        segs, dists = self._edges_with_dists(self.sim.nodes, self.sim.cfg["comm_range"])
        self.edge_norm = mcolors.Normalize(vmin=0, vmax=self.sim.cfg["comm_range"])
        self.edge_cmap = cm.plasma
        self.lines = LineCollection(
            segs,
            linewidths=2.0,
            alpha=0.75,
            colors=self.edge_cmap(self.edge_norm(dists)),
        )
        self.ax.add_collection(self.lines)

        # Route trace layer (fading, thin dotted) for DataMsg deliveries
        self.tracer = PathTracer2D(
            ttl_s=self.sim.cfg["trace_ttl_s"],
            max_segments=self.sim.cfg["trace_max_segments"],
        )
        self.trace_lines = LineCollection([], linewidths=1.0, alpha=0.9, colors=(0.2, 0.95, 0.4, 0.9))
        self.trace_lines.set_linestyle("dotted")
        self.ax.add_collection(self.trace_lines)

        # Bind nodes to tracer sink (DataMsg delivery only)
        for n in self.sim.nodes:
            n._trace_sink = lambda path_ids, self=self: self.tracer.add_path(self.sim.nodes, path_ids)

        # HUD (slightly lower so it doesn't overlap dv_note)
        self.hud = self.fig.text(
            0.01,
            0.965,
            "",
            ha="left",
            va="top",
            fontsize=11,
        )
        # DV note at the very top center
        self.dv_note = self.fig.text(
            0.5,
            0.99,
            f"Number under each node = DV cost to node {self.dv_dest} (∞ = no route yet). "
            f"Press LEFT/RIGHT to change reference node.",
            ha="center",
            va="top",
            fontsize=9,
        )

        # Buttons (Play/Pause, Clear Traces)
        plt.subplots_adjust(bottom=0.12)
        ax_play = self.fig.add_axes([0.74, 0.02, 0.10, 0.06])
        ax_clear = self.fig.add_axes([0.86, 0.02, 0.10, 0.06])
        self.btn_play = Button(ax_play, "Play/Pause")
        self.btn_clear = Button(ax_clear, "Clear Traces")
        self.btn_play.on_clicked(self._toggle_pause)
        self.btn_clear.on_clicked(self._clear_traces)

        # Keyboard shortcuts too
        self.fig.canvas.mpl_connect("key_press_event", self._on_key)

        # Animation
        interval_ms = int(1000 / self.sim.cfg["fps"])
        self.anim = FuncAnimation(self.fig, self.update, interval=interval_ms, blit=False)

    def _toggle_pause(self, _event=None):
        self.paused = not self.paused

    def _clear_traces(self, _event):
        self.tracer.buff.clear()

    def _on_key(self, event):
        if event.key in ("p", "P", " "):  # spacebar also pauses
            self._toggle_pause(None)
        elif event.key in ("c", "C"):
            self._clear_traces(None)
        elif event.key in ("left", "right"):
            # Cycle through destination IDs (all-to-all DV, one dest slice at a time)
            n_nodes = len(self.sim.nodes)
            if n_nodes == 0:
                return
            if event.key == "left":
                self.dv_dest = (self.dv_dest - 1) % n_nodes
            else:  # "right"
                self.dv_dest = (self.dv_dest + 1) % n_nodes

            # Reset highlight state so changes for this new dv_dest are visible
            self.prev_costs = {n.nid: None for n in self.sim.nodes}
            self.dv_last_change_ts = {n.nid: 0.0 for n in self.sim.nodes}

            # Update the legend text
            self.dv_note.set_text(
                f"Number under each node = DV cost to node {self.dv_dest} (∞ = no route yet). "
                f"Press LEFT/RIGHT to change destination."
            )
        elif event.key in ("q", "Q", "escape"):
            plt.close(self.fig)

    @staticmethod
    def _edges_with_dists(nodes: List[Any], comm_range: float):
        segs = []
        dists = []
        for i in range(len(nodes)):
            xi, yi, _ = nodes[i].pos
            for j in range(i + 1, len(nodes)):
                xj, yj, _ = nodes[j].pos
                dx, dy = xi - xj, yi - yj
                dist2 = dx * dx + dy * dy
                if dist2 <= comm_range ** 2:
                    segs.append(((xi, yi), (xj, yj)))
                    dists.append(math.sqrt(dist2))
        return segs, dists

    def update(self, _frame):
        # even if paused, return artists so FuncAnimation keeps running
        if not self.paused:
            xs = [n.pos[0] for n in self.sim.nodes]
            ys = [n.pos[1] for n in self.sim.nodes]
            self.scatter.set_offsets(list(zip(xs, ys)))

            # Update node ID labels above nodes
            for lbl, x, y in zip(self.labels, xs, ys):
                lbl.set_position((x, y + self.sim.cfg["label_offset"]))

            # Update DV cost labels (cost to dv_dest) with highlighting on change
            dv_off = self.sim.cfg["label_offset"] + 14.0
            now = time.time()
            for node, dv_lbl, x, y in zip(self.sim.nodes, self.dv_labels, xs, ys):
                route = node.rt.get(self.dv_dest)
                if route is None:
                    cost_val = None
                    txt = "∞"
                else:
                    cost_val = route.cost
                    txt = f"{route.cost:.1f}"

                # Detect changes
                prev = self.prev_costs[node.nid]
                if (
                    (prev is None and cost_val is not None)
                    or (prev is not None and cost_val is None)
                    or (prev is not None and cost_val is not None and abs(prev - cost_val) > 1e-6)
                ):
                    self.prev_costs[node.nid] = cost_val
                    self.dv_last_change_ts[node.nid] = now

                # Highlight label briefly if it changed recently
                age = now - self.dv_last_change_ts[node.nid]
                if age < self.dv_highlight_duration:
                    dv_lbl.set_color("yellow")
                    dv_lbl.set_fontweight("bold")
                else:
                    dv_lbl.set_color("white")
                    dv_lbl.set_fontweight("normal")

                dv_lbl.set_text(txt)
                dv_lbl.set_position((x, y - dv_off))

            # Neighbor links
            segs, dists = self._edges_with_dists(self.sim.nodes, self.sim.cfg["comm_range"])
            self.lines.set_segments(segs)
            if dists:
                self.lines.set_color(self.edge_cmap(self.edge_norm(dists)))

            # Sweep + draw route traces (fade)
            self.tracer.sweeper()
            segs_fade, alphas = self.tracer.segments_and_alphas()
            colors = []
            base = (0.2, 0.95, 0.4)  # neon green
            for a in alphas:
                colors.append((base[0], base[1], base[2], a))
            self.trace_lines.set_segments(segs_fade)
            if colors:
                self.trace_lines.set_color(colors)

            # HUD stats (Data only)
            tot_gen = sum(n.generated for n in self.sim.nodes)
            tot_del = sum(n.delivered for n in self.sim.nodes)
            dr = (tot_del / tot_gen) if tot_gen else 0.0
            all_hops = [h for n in self.sim.nodes for h in n.hops_used]
            avg_hops = (sum(all_hops) / len(all_hops)) if all_hops else 0.0
            all_lat = [l for n in self.sim.nodes for l in n.latencies]
            avg_lat = (sum(all_lat) / len(all_lat)) if all_lat else 0.0

            self.hud.set_text(
                f"Nodes: {len(self.sim.nodes)}   Range: {self.sim.cfg['comm_range']} m   "
                f"Generated (Data): {tot_gen}   Delivered: {tot_del}   DR: {dr:.2f}   "
                f"Avg hops: {avg_hops:.2f}   Avg latency: {avg_lat:.3f}s"
            )

        return self.scatter, self.lines, self.trace_lines, *self.labels, *self.dv_labels, self.hud


def run_live_viz(sim: Simulation):
    """Run asyncio simulation in a background thread and show a live view."""

    def _run():
        asyncio.run(sim.run())

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    LiveArtist2D(sim)
    plt.show()
    sim.report()
