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
- `show_routing_tables`: Enable detailed routing table panel (default: True)
- `rt_display_nodes`: List of node IDs to show routing tables for (default: [0, 1])

## Usage Instructions

### Prerequisites

Before running the simulation, ensure you have:
- Python 3.8 or higher installed
- matplotlib library installed (`pip install matplotlib`)
- A display environment (not headless) for visualization

### Running the Simulation

#### Basic Command
```bash
cd drone-mesh-network
python main.py
```

#### Expected Output

**Console Output:**
```
Starting simulation in 2D 
(simplified MAC, secure-ish handshake, DV cost labels + aging, DV dest cycling)
```

**Visualization Window:**
- A matplotlib window opens showing the 2D simulation area
- Drone nodes appear as colored circles with ID labels
- Gray lines connect nodes within communication range
- Colored fading traces show data packet routes
- Title bar displays: simulation time, packet delivery ratio, latency, and hop count
- **Routing Table Panel** (if enabled): Shows real-time routing tables with:
  - Complete cost data to all destinations
  - Next hop information
  - Route age (time since last update)
  - Recent updates highlighted with asterisk (*)

**Simulation Flow:**
1. Nodes initialize at random positions
2. Nodes begin moving toward random waypoints
3. Hello beacons discover neighbors (gray links appear)
4. Distance vector updates establish routes
5. Application layer initiates handshakes (SessionReq/SessionAck)
6. Data packets flow along established routes (colored traces)
7. Metrics update in real-time in the title bar

### Script Purposes

#### Core Scripts

**`main.py`** - Entry Point
- **Purpose**: Initializes and launches the simulation
- **Function**: Creates simulation instance, builds network, and starts visualization
- **Usage**: `python main.py`

**`sim.py`** - Simulation Orchestrator
- **Purpose**: Manages the simulation lifecycle and coordinates all components
- **Key Functions**:
  - `build()`: Creates drone nodes and attaches them to the channel
  - `run()`: Executes simulation for configured duration with all node tasks
  - `report()`: Calculates performance statistics (PDR, latency, hop count)

**`config.py`** - Configuration Manager
- **Purpose**: Centralizes all simulation parameters
- **Key Variables**:
  - `SIM_CONFIG`: Dictionary containing all tunable parameters
  - Network settings (nodes, range, world size)
  - Protocol timings (hello, DV, handshake periods)
  - Mobility parameters (speed, waypoint pause)
  - MAC layer settings (backoff, transmission duration)
  - Visualization options (FPS, trace duration, node size)

#### Node and Network Scripts

**`node.py`** - Drone Node Implementation
- **Purpose**: Implements individual drone behavior and protocol stack
- **Key Functions**:
  - `mobility_task()`: Updates node position toward current waypoint
  - `hello_task()`: Broadcasts neighbor discovery beacons periodically
  - `dv_task()`: Sends distance vector routing updates
  - `app_task()`: Initiates handshakes and sends data packets
  - `rx_loop()`: Receives and processes incoming messages
  - `neighbor_watch_task()`: Ages out stale neighbors based on timeout
  - `_step_toward_waypoint()`: Calculates and applies incremental movement
  - `_pick_new_waypoint()`: Selects new random destination

**`channel.py`** - Wireless Channel Simulation
- **Purpose**: Simulates the wireless medium with simplified CSMA/CA MAC layer
- **Key Functions**:
  - `broadcast()`: Transmits messages to all nodes in communication range
  - `_wait_for_idle_and_backoff()`: Implements carrier sensing and random backoff
  - `_reserve_channel()`: Marks channel as busy during transmission
  - `_deliver_in_range()`: Delivers packets to nodes within range with delay/jitter

**`routing.py`** - Distance Vector Routing
- **Purpose**: Implements Bellman-Ford routing algorithm
- **Key Functions**:
  - `ensure_one_hop()`: Establishes direct route to neighbor
  - `apply_distance_vector()`: Processes received distance vectors (Bellman-Ford relaxation)

**`messages.py`** - Message Definitions
- **Purpose**: Defines all message types used in the protocol
- **Message Types**:
  - `HelloMsg`: Neighbor discovery beacon with position and sequence number
  - `DVMsg`: Distance vector routing update with full routing table
  - `SessionReq`: Handshake initiation request from source to destination
  - `SessionAck`: Handshake acknowledgment from destination back to source
  - `DataMsg`: Application data packet with payload and path tracking

**`viz2d.py`** - 2D Visualization
- **Purpose**: Provides real-time graphical display of network state
- **Key Functions**:
  - `run_live_viz()`: Main visualization loop with matplotlib animation
  - `PathTracer2D`: Manages fading route traces for delivered packets
  - `_update_frame()`: Refreshes visualization with current node positions and connectivity
  - `add_path()`: Records packet routes for visual display

### Example Commands

#### Standard Simulation (4 nodes, 120 seconds)
```bash
python main.py
```

#### Modify Configuration Before Running
Edit `config.py` before running:
```python
SIM_CONFIG = {
    "num_nodes": 8,              # Increase network size
    "comm_range": 300.0,         # Extend communication range
    "sim_time_s": 180.0,         # Run for 3 minutes
    "speed_mps": (5.0, 15.0),    # Reduce speed for stability
}
```
Then run: `python main.py`

#### Debug Mode (Enable DV Logging)
Edit `config.py`:
```python
SIM_CONFIG = {
    ...
    "log_dv_changes": True,      # See routing updates in console
    ...
}
```

#### Testing with Routing Table Visualization (2 nodes)
Edit `config.py` to verify routing table updates:
```python
SIM_CONFIG = {
    "num_nodes": 2,                    # Simplified network for testing
    "show_routing_tables": True,       # Enable RT panel
    "rt_display_nodes": [0, 1],        # Show both nodes
    "comm_range": 260.0,               # Ensure nodes can communicate
    "sim_time_s": 60.0,                # Shorter test duration
    ...
}
```
This configuration displays a side panel showing:
- Complete routing tables for nodes 0 and 1
- Real-time cost updates (highlighted with * when changed)
- Next hop information for each destination
- Route age to verify table freshness
Then run: `python main.py`

### Interactive Controls

**During Simulation:**
- **Pause**: Click "Pause" button in visualization window
- **Resume**: Click "Resume" button to continue
- **Stop**: Press `Ctrl+C` in terminal or close window

### Expected Inputs

**Configuration File (`config.py`):**
- All simulation parameters are read from `SIM_CONFIG` dictionary
- No command-line arguments or runtime inputs required
- Modify configuration before execution

**Random Seed:**
- Default seed (42) ensures reproducible results
- Change seed value in config for different random scenarios

### Expected Outputs

**Visual Output:**
- Real-time animated network topology
- Node movement and connectivity changes
- Data packet routing traces (colored fading lines)
- Performance metrics in window title

**Console Output:**
```
Starting simulation in 2D 
(simplified MAC, secure-ish handshake, DV cost labels + aging, DV dest cycling)
[Occasional routing or MAC layer debug messages if enabled]
```

**Internal Metrics (tracked throughout):**
- Packet Delivery Ratio (PDR): Percentage of successfully delivered packets
- Average End-to-End Latency: Mean time from source to destination
- Average Hop Count: Mean number of hops per delivered packet

### Performance Notes

**Typical Execution:**
- 4 nodes, 120s simulation: ~2-3 minutes real-time
- 10 nodes, 180s simulation: ~5-8 minutes real-time
- Performance depends on: number of nodes, FPS, and system capabilities

**Resource Usage:**
- CPU: Moderate (visualization dominates)
- Memory: <100MB for typical configurations
- Disk: None (no file I/O during simulation)

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
