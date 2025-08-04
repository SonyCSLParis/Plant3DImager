# System Architecture

This document presents the system architecture and the interactions between different modules.

## Component Diagram

```
┌─────────────────┐     ┌───────────────────┐
│                 │     │                   │
│  IMAGE          │     │  LEAF             │
│  ACQUISITION    │     │  TARGETING        │
│                 │     │                   │
└────────┬────────┘     └─────────┬─────────┘
         │                        │
         │                        │
         ▼                        ▼
┌──────────────────────────────────────────┐
│                                          │
│           CORE                           │
│  ┌────────────┐ ┌────────────┐           │
│  │  Hardware  │ │  Geometry  │           │
│  └────────────┘ └────────────┘           │
│  ┌────────────┐ ┌────────────┐           │
│  │  Data      │ │  Utils     │           │
│  └────────────┘ └────────────┘           │
│                                          │
└──────────────┬───────────────┬───────────┘
               │               │
               ▼               ▼
┌─────────────────┐    ┌───────────────────┐
│                 │    │                   │
│  MANUAL         │    │  SERVER           │
│  CONTROL        │    │  SYNC             │
│                 │    │                   │
└─────────────────┘    └───────────────────┘
```

## Integration with ROMI Framework

This system is built on top of the [ROMI (RObotics for MIcrofarms)](https://github.com/romi/romi-apps) framework and [Plant-3D-Vision](https://github.com/romi/plant-3d-vision) pipeline. These provide the foundational components for:

1. **Hardware Control**
   - The ROMI framework provides Python wrappers for controlling CNC machines and cameras
   - Our `core/hardware` controllers use ROMI's API to interact with physical devices

2. **3D Reconstruction**
   - The Plant-3D-Vision pipeline processes images to create 3D point clouds
   - The `sync` module coordinates with the server to run this pipeline

3. **Data Flow**
   - Image data → ROMI Plant-3D-Vision → Point Cloud → Our targeting system

The synchronization module (`server_sync.py`) acts as a bridge between our acquisition system and the ROMI Plant-3D-Vision pipeline running on the server. It:

1. Uploads acquired images to the server
2. Triggers the Plant-3D-Vision pipeline via `romi_run_task` commands
3. Downloads the resulting point cloud for local processing

### ROMI Task Sequence

```
Clean → Upload Images → PointCloud Generation → Download Results
```

## Module Descriptions

### Core Components

The core directory contains components shared across all modules:

1. **Hardware Controllers**
   - `CNCController`: Manages XYZ movements of the robot
   - `CameraController`: Handles photo capture
   - `GimbalController`: Controls camera orientation

2. **Geometry Utilities**
   - `path_calculator.py`: Plans circular trajectories and paths
   - `angle_calculator.py`: Calculates camera angles

3. **Data Management**
   - `storage_manager.py`: Manages file and directory operations

4. **Utilities**
   - `config.py`: Loads and provides access to configuration

### Acquisition Module

The acquisition module handles circular image capture:

- `circle_acquisition.py`: Main class for circular acquisition
- `metadata_generator.py`: Generates metadata for acquired images

### Targeting Module

The targeting module handles leaf detection and targeting:

- `leaf_targeting.py`: Main class for leaf targeting
- `data_manager.py`: Loads and processes point cloud data
- `leaf_analyzer.py`: Detects and analyzes leaves
- `path_planner.py`: Plans paths to target leaves
- `robot_controller.py`: Controls robot movements for targeting
- `interactive_selector.py`: Allows interactive leaf selection
- `visualization.py`: Visualizes point clouds and trajectories

### Manual Control Module

- `manual_controller.py`: Provides direct control of the robot

### Synchronization Module

- `server_sync.py`: Manages data synchronization with server
- `ssh_manager.py`: Handles SSH connections and commands

## Complete Workflow

1. **Image Acquisition**
   - Circular path around the plant
   - Photos taken at equidistant positions
   - Metadata generation (camera position, etc.)

2. **Server Synchronization**
   - Transfer images to server
   - Launch 3D processing
   - Retrieve point cloud

3. **Leaf Targeting**
   - Load point cloud
   - Detect leaves via Louvain algorithm
   - Calculate optimal viewing points
   - Move robot to leaves
   - Take individual leaf photos

## Hardware Interactions

- **CNC Controller**: Controls XYZ movements of the robot
- **Camera Controller**: Manages photo capture
- **Gimbal Controller**: Orients the camera toward targets

## Results Structure

```
results/
├── plant_acquisition/
│   └── circular_scan_YYYYMMDD-HHMMSS/
│       ├── images/              # Raw photos
│       ├── metadata/            # Metadata
│       │   └── images/          # Per-image metadata
│       ├── files.json           # File list
│       └── scan.toml            # Scan configuration
│
├── leaf_targeting/
│   └── leaf_analysis_YYYYMMDD-HHMMSS/
│       ├── images/              # Leaf photos
│       ├── analysis/            # Analysis data
│       └── visualizations/      # Visualizations
│
└── pointclouds/                 # Point clouds
```

## Technical Details

### Circular Acquisition Process

1. The robot follows a circular path around the plant
2. At each position:
   - The gimbal orients the camera toward the target point
   - The system waits for stabilization
   - A photo is taken and metadata recorded

### Leaf Detection Algorithm

1. Point cloud is cropped to focus on plant surfaces
2. Alpha shape is calculated to extract surface points
3. A connectivity graph is built between points
4. Louvain community detection finds leaf clusters
5. Planes are fitted to each cluster and normals calculated
6. Target points are calculated at a specified distance from each leaf

### Gimbal Control Mechanism

The gimbal controller calculates pan and tilt angles to aim at targets:
- Pan: Horizontal angle (rotation around Z axis)
- Tilt: Vertical angle (rotation around X axis)

### Data Flow Diagram

```
┌───────────┐     ┌───────────┐     ┌────────────┐     ┌────────────┐
│           │     │           │     │            │     │            │
│  Circular │────>│  Server   │────>│  Point     │────>│  Leaf      │
│  Photos   │     │  Sync     │     │  Cloud     │     │  Detection │
│           │     │           │     │            │     │            │
└───────────┘     └───────────┘     └────────────┘     └──────┬─────┘
                                                              │
                                                              │
┌───────────┐     ┌───────────┐     ┌────────────┐     ┌──────▼─────┐
│           │     │           │     │            │     │            │
│  Leaf     │<────│  Robot    │<────│  Path      │<────│  Target    │
│  Photos   │     │  Control  │     │  Planning  │     │  Points    │
│           │     │           │     │            │     │            │
└───────────┘     └───────────┘     └────────────┘     └────────────┘
```

## Extension Points

The modular architecture allows for several extension points:

1. **New Acquisition Patterns**
   - Add new path generation algorithms in `path_calculator.py`
   - Create new acquisition classes similar to `circle_acquisition.py`

2. **Enhanced Leaf Detection**
   - Implement alternative detection algorithms in `leaf_analyzer.py`
   - Add new visualization methods in `visualization.py`

3. **Additional Hardware Support**
   - Extend hardware controllers in the `core/hardware/` directory
   - Implement new interfaces in `robot_controller.py`
