# Plant Imaging and Leaf Targeting System

A modular robotic system for plant phenotyping that performs circular image acquisition and precise targeting of individual leaves.

![System Overview](https://example.com/system_overview.png) <!-- You can add a system image here -->

## Key Features

- **Circular Image Acquisition**: Capture images around plants along one or two circular paths with precise camera orientation
- **Automated Leaf Targeting**: Identify and photograph individual leaves using 3D point cloud analysis
- **Interactive Leaf Selection**: Visualize and select specific leaves for detailed imaging
- **Manual Robot Control**: Fine-grained positioning for custom imaging tasks
- **Server Integration**: Automatic synchronization with a server for 3D reconstruction via the ROMI Plant-3D-Vision pipeline

## System Architecture

```
┌───────────────────────────────────────────┐
│                 CORE                      │
│  ┌────────────┐  ┌────────────┐           │
│  │  Hardware  │  │  Geometry  │           │
│  └────────────┘  └────────────┘           │
│  ┌────────────┐  ┌────────────┐           │
│  │  Data      │  │  Utils     │           │
│  └────────────┘  └────────────┘           │
└─┬─────────────┬──────────┬────────────┬───┘
  │             │          │            │
  ▼             ▼          ▼            ▼
┌──────────┐ ┌────────┐ ┌────────┐ ┌─────────┐
│  IMAGE   │ │ SERVER │ │  LEAF  │ │ MANUAL  │
│ACQUISITION│→│  SYNC  │→│TARGETING│ │ CONTROL │
└──────────┘ └────────┘ └────────┘ └─────────┘
    Data Flow ────────────────→    Independent
```

For detailed architecture information, see the [architecture documentation](doc/architecture.md).

## Installation

### Prerequisites

- Python 3.7+
- Required libraries: open3d, numpy, scipy, matplotlib, paramiko, networkx
- Arduino setup for gimbal control
- [ROMI framework](https://github.com/romi/romi-apps) for hardware interfacing
- [Plant-3D-Vision](https://github.com/romi/plant-3d-vision) for 3D reconstruction

### Quick Setup

1. Clone the repository:
```bash
git clone https://github.com/your-username/plant-imaging-system.git
cd plant-imaging-system
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure system parameters in `config.json`

## Usage

### Circular Image Acquisition

```bash
# Acquire images around a plant with 80 positions on a single circle
python main.py --mode acquisition --circles 1 --positions 80

# Acquire images with two circles at different heights
python main.py --mode acquisition --circles 2 --positions 60 --z-offset 0.2
```

### Leaf Targeting

```bash
# Process a point cloud and target individual leaves
python main.py --mode targeting --point_cloud path/to/PointCloud.ply

# With custom parameters
python main.py --mode targeting --point_cloud path/to/PointCloud.ply --scale 0.001 --louvain_coeff 0.5 --distance 0.4
```

### Manual Control

```bash
# Start manual control mode
python main.py --mode manual

# Command format: x y z [pan] [tilt] [photo]
# Example commands:
# 0.3 0.4 0.2           # Move to position
# 0.3 0.4 0.2 45 30     # Move and orient camera
# 0.3 0.4 0.2 45 30 1   # Move, orient, and take photo
```

### Complete Workflow

```bash
# Run the full workflow: acquisition → synchronization → targeting
python main.py --mode workflow

# Skip specific steps if needed
python main.py --mode workflow --skip-acquisition --point-cloud path/to/existing.ply
```

## Documentation

- [User Guide](doc/user_guide.md) - Detailed usage instructions
- [Configuration Guide](doc/configuration.md) - Configuration parameters reference
- [Architecture](doc/architecture.md) - System architecture and technical details

## Project Structure

- `acquisition/` - Circular image acquisition
- `targeting/` - Leaf targeting and analysis
- `manual_control/` - Manual control system
- `sync/` - Server synchronization
- `core/` - Shared components (hardware, geometry, data, utils)
- `scripts/` - Execution scripts
- `results/` - Results storage

## License

[MIT License](LICENSE)

## Acknowledgments

This project builds upon the [ROMI (RObotics for MIcrofarms)](https://github.com/romi/romi-apps) framework and [Plant-3D-Vision](https://github.com/romi/plant-3d-vision) pipeline.