# Drone Mesh Network Simulator

A Python-based simulator for a wireless mesh network of autonomous drones with dynamic routing, mobility models, and real-time 2D visualization.

## Overview

This project simulates a Flying ad-hoc network (FANET) of drone nodes that:
- Move autonomously using waypoint-based mobility
- Discover neighbors via periodic Hello beacons
- Exchange distance-vector routing information
- Establish secure handshakes before data transmission
- Use simplified CSMA/CA medium access control
- Visualize network topology and data paths in real-time

## Features

- **Distance Vector Routing**: Bellman-Ford-based routing with neighbor aging to adapt to mobility
- **Secure Handshake Protocol**: Session establishment before data exchange (SessionReq → SessionAck → DataMsg)
- **Simplified MAC Layer**: CSMA/CA-style collision avoidance with backoff and channel sensing
- **Waypoint Mobility**: Nodes move between random waypoints with configurable speeds and pause times
- **Real-time Visualization**: Live 2D animation showing node positions, connectivity, and data paths
- **Performance Metrics**: Tracks packet delivery ratio, end-to-end latency, and hop counts

## Requirements

### Python Version
- Python 3.8 or higher

### Dependencies

```
matplotlib>=3.5.0
```

Install dependencies using:
```bash
pip install matplotlib
```

## Project Structure

```
drone-mesh-network/
├── main.py           # Entry point for the simulation
├── sim.py            # Simulation orchestrator
├── config.py         # Configuration parameters
├── node.py           # DroneNode implementation (mobility, routing, MAC)
├── channel.py        # WirelessChannel (medium simulation with MAC)
├── routing.py        # Distance vector routing algorithms
├── messages.py       # Message type definitions (Hello, DV, SessionReq, etc.)
├── viz2d.py          # 2D visualization with matplotlib
└── README.md         # This file
```

## Configuration

Edit `config.py` to customize simulation parameters:

### Network Parameters
- `num_nodes`: Number of drone nodes (default: 4)
- `world_size`: Simulation area in meters (default: 1000m × 700m)
- `comm_range`: Radio communication range (default: 260m)

### Protocol Timings
- `hello_period_s`: Neighbor discovery beacon interval (default: 0.6s)
- `dv_period_s`: Routing update interval (default: 1.2s)
- `app_send_period_s`: Application handshake period (default: 1.6s)
- `neighbor_timeout_s`: Neighbor expiry timeout (default: 2.0s)

### Mobility Settings
- `speed_mps`: Drone speed range in m/s (default: 10-22 m/s)
- `waypoint_pause_s`: Pause time at waypoints (default: 0-0.4s)
- `mobility_step_s`: Mobility update interval (default: 0.2s)

### MAC Layer
- `mac_min_backoff_s`: Minimum backoff time (default: 0.001s)
- `mac_max_backoff_s`: Maximum backoff time (default: 0.006s)
- `mac_tx_duration_s`: Transmission duration (default: 0.003s)

### Simulation
- `sim_time_s`: Total simulation duration (default: 120s)
- `seed`: Random seed for reproducibility (default: 42)

### Visualization
- `fps`: Frames per second (default: 15)
- `trace_ttl_s`: Route trace display duration (default: 6.0s)
- `node_size`: Node marker size (default: 110)

## How to Run

### Basic Execution

1. **Navigate to the project directory:**
   ```bash
   cd drone-mesh-network
   ```

2. **Run the simulation:**
   ```bash
   python main.py
   ```

3. **The visualization window will open automatically**, showing:
   - Drone positions (colored circles with node IDs)
   - Communication links (gray lines between neighbors)
   - Data paths (colored fading traces showing packet routes)
   - Simulation time and metrics in the title

4. **Stop the simulation:**
   - Press `Ctrl+C` in the terminal, or
   - Close the visualization window

### Visualization Controls

- **Pause/Resume**: Click the "Pause"/"Resume" button in the visualization window
- **Real-time Updates**: The display refreshes at the configured FPS
- **Path Traces**: Recent data packet routes are shown as fading colored lines

### Expected Output

During simulation, you'll see:
- Console output indicating simulation start
- A live matplotlib window showing the network topology
- Nodes moving around the simulation area
- Links appearing/disappearing as nodes move in/out of range
- Colored traces showing successful data transmissions

At the end of the simulation, performance metrics are calculated (internally tracked):
- Packet delivery ratio
- Average end-to-end latency
- Average hop count per packet

## Understanding the Simulation

### Network Layers

1. **Application Layer** (`app_task`):
   - Periodically initiates handshakes with random destinations
   - Sends data packets after successful handshake

2. **Routing Layer** (`dv_task`):
   - Maintains routing table using distance vector protocol
   - Periodically broadcasts routing updates
   - Ages out stale neighbors

3. **MAC Layer** (`channel.py`):
   - Implements carrier sensing and random backoff
   - Prevents simultaneous transmissions
   - Simulates realistic medium access delays

4. **Physical Layer** (`channel.py`):
   - Delivers packets to nodes within communication range
   - Adds propagation delay and jitter

### Message Flow

1. **Neighbor Discovery**: HelloMsg broadcasts → neighbors update neighbor sets
2. **Route Discovery**: DVMsg exchanges → routing tables converge
3. **Session Setup**: SessionReq → SessionAck handshake
4. **Data Transfer**: DataMsg routed hop-by-hop to destination
5. **Path Visualization**: Successful routes traced in visualization

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'matplotlib'`
- **Solution**: Install matplotlib: `pip install matplotlib`

**Issue**: Visualization window doesn't appear
- **Solution**: Ensure you're running in an environment with GUI support (not headless)

**Issue**: Simulation runs too slowly
- **Solution**: Reduce `num_nodes` or increase `mobility_step_s` in `config.py`

**Issue**: No data packets being delivered
- **Solution**: 
  - Increase `comm_range` for better connectivity
  - Reduce `speed_mps` for more stable routes
  - Increase `sim_time_s` to allow more time for route convergence

## Advanced Usage

### Modifying Network Size

To test with more nodes:
```python
# In config.py
SIM_CONFIG = {
    "num_nodes": 10,  # Increase from 4 to 10
    "world_size": (2000.0, 1500.0),  # Scale up area
    ...
}
```

### Enabling Debug Logging

Enable distance vector logging:
```python
# In config.py
SIM_CONFIG = {
    ...
    "log_dv_changes": True,
    ...
}
```

### Custom Mobility Patterns

Modify the waypoint selection in `node.py` → `_pick_waypoint()` method to implement different mobility models.

## Performance Tuning

For optimal performance:
- **Larger networks**: Increase `world_size` proportionally with `num_nodes`
- **Faster convergence**: Decrease `dv_period_s` and `hello_period_s`
- **Stable routes**: Reduce `speed_mps` or increase `neighbor_timeout_s`
- **Lower CPU usage**: Reduce `fps` and increase `mobility_step_s`

## Technical Details

### Routing Algorithm
- **Protocol**: Distance Vector (Bellman-Ford)
- **Metric**: Hop count
- **Updates**: Periodic and event-driven (neighbor loss)
- **Loop prevention**: Split horizon with poisoned reverse

### MAC Protocol
- **Type**: CSMA/CA-inspired
- **Features**: Carrier sensing, random backoff, channel reservation
- **Collision handling**: Simplified (no retransmissions)

### Security
- **Handshake**: Required before data transmission
- **Session IDs**: Unique per communication pair
- **Authentication**: Simplified (session-based)



## Contact

For questions or issues, please open an issue on the project repository.
- Isaac Nkrumah <isaac.nkrumah@slu.edu>
- Faisal Wahabu <faisal.wahabu@slu.edu>
- Kwabena Adjei Omanhene-Gyimah <kwabenaadjei.omanhenegyimah@slu.edu>
