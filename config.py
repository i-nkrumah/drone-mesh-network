import random
import matplotlib.pyplot as plt

SIM_CONFIG = {
    "num_nodes": 4,
    "world_size": (1000.0, 700.0),    # meters (X, Y)
    "comm_range": 260.0,              # meters radio range (approx. Wi-Fi / ISM range)
    "hello_period_s": 0.6,            # neighbor beacons
    "dv_period_s": 1.2,               # routing periodic updates
    "mobility_step_s": 0.20,          # mobility tick
    "app_send_period_s": 1.6,         # handshake initiation period
    "sim_time_s": 120.0,              # total simulation time
    "speed_mps": (10.0, 22.0),        # waypoint speed range
    "waypoint_pause_s": (0.0, 0.4),
    "channel_jitter_s": (0.002, 0.020),
    "channel_base_delay_s": 0.001,
    "prop_speed_mps": 3e8,
    "max_per_hop_delay_s": 0.015,     # clamp per-hop delay for visibility
    "data_payload_bytes": 32,
    "app_pairs_per_period": 2,        # handshake initiations per period
    "seed": 42,
    "log_dv_changes": True,
    # Simplified MAC parameters (CSMA/CA-style)
    "mac_min_backoff_s": 0.001,
    "mac_max_backoff_s": 0.006,
    "mac_slot_s": 0.001,              # sensing slot time
    "mac_tx_duration_s": 0.003,       # on-air duration for a frame
    # Neighbor aging (to make DV react to mobility)
    "neighbor_timeout_s": 2.0,        # time w/o Hello before a neighbor is considered gone
    # Viz
    "node_size": 110,
    "label_offset": 12.0,
    "fps": 15,                        # viz FPS
    # Route trace styling
    "trace_ttl_s": 6.0,               # how long a trace stays on screen
    "trace_max_segments": 600,        # cap to avoid unbounded memory
    # Routing table visualization
    "show_routing_tables": True,     # Show detailed routing tables in side panel
    "rt_display_nodes": [0, 1],      # Which nodes to show routing tables for (empty = all)
}

# Global seed + style
random.seed(SIM_CONFIG["seed"])
plt.style.use("seaborn-v0_8-darkgrid")
