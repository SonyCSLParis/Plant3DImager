# Plant Imaging and Leaf Targeting System

A modular robotic system for circular plant image acquisition and precise targeting of individual leaves.

## Features

- Circular image acquisition around plants (1 or 2 circles)
- Automatic leaf targeting based on 3D analysis
- Manual robot control for custom positioning
- Server synchronization for point cloud processing

## Installation

### Prerequisites

- Python 3.7+
- Libraries: open3d, numpy, scipy, matplotlib, paramiko, networkx
- Arduino drivers for gimbal control
- [ROMI framework](https://github.com/romi/romi-apps) for CNC control and hardware interfaces
- [Plant-3D-Vision](https://github.com/romi/plant-3d-vision) for 3D reconstruction and analysis

### Installing Dependencies

```bash
pip install -r requirements.txt
```

### ROMI Setup

1. Clone and install ROMI repositories:
```bash
git clone https://github.com/romi/romi-apps.git
git clone https://github.com/romi/plant-3d-vision.git

# Install ROMI apps
cd romi-apps
pip install -e .

# Install Plant-3D-Vision
cd ../plant-3d-vision
pip install -e .
```

2. Make sure ROMI configuration is properly set in your `config.json` file.

## Quick Start

### 1. Circular Image Acquisition

```bash
python main.py --mode acquisition --circles 1 --positions 80
```

### 2. Leaf Targeting

```bash
python main.py --mode targeting --point_cloud path/to/PointCloud.ply
```

### 3. Manual Control

```bash
python main.py --mode manual
```

### 4. Complete Workflow (acquisition + sync + targeting)

```bash
python main.py --mode workflow
```

## Project Structure

- `acquisition/` - Circular image acquisition module
- `targeting/` - Leaf targeting module
- `manual_control/` - Manual control module
- `sync/` - Server synchronization module
- `core/` - Shared components (hardware, geometry, data, utils)
- `scripts/` - Execution scripts for each module
- `results/` - Results storage directory

## Configuration

The `config.json` file contains the main system parameters. See the configuration documentation for more details.

## Documentation

Additional documentation can be found in the `doc/` directory:

- `user_guide.md` - Detailed usage instructions
- `configuration.md` - Configuration parameters reference
- `architecture.md` - System architecture overview
