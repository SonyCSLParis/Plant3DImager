# Configuration Documentation

This document describes the parameters available in the `config.json` file and their effects on the system.

## General Parameters

| Parameter | Description | Default Value | Unit |
|-----------|-------------|---------------|------|
| `TARGET_POINT` | Target point for camera orientation | [0.375, 0.35, 0.30] | m |
| `CENTER_POINT` | Center of acquisition circle | [0.375, 0.35, 0.00] | m |
| `CIRCLE_RADIUS` | Radius of acquisition circle | 0.30 | m |
| `NUM_POSITIONS` | Number of positions on the circle | 80 | - |
| `Z_OFFSET` | Z offset between two circles | 0.20 | m |

## Hardware Parameters

| Parameter | Description | Default Value | Unit |
|-----------|-------------|---------------|------|
| `ARDUINO_PORT` | Arduino serial port for gimbal | "/dev/ttyACM0" | - |
| `CNC_SPEED` | CNC movement speed | 0.1 | m/s |
| `UPDATE_INTERVAL` | Update interval during movement | 0.1 | s |
| `STABILIZATION_TIME` | Stabilization time before photo | 3.0 | s |

## Storage Parameters

| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `RESULTS_DIR` | Main directory for results | "results" |
| `ACQUISITION_DIR` | Subdirectory for acquisition | "plant_acquisition" |
| `TARGETING_DIR` | Subdirectory for targeting | "leaf_targeting" |

## Synchronization Parameters

| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `SSH_HOST` | SSH server address | "10.0.7.22" |
| `SSH_USER` | SSH username | "ayman" |
| `KEY_PATH` | Path to SSH key | "/home/romi/.ssh/id_rsa" |
| `REMOTE_WORK_PATH` | Remote working directory path | "/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/Col_A_2021-01-29/" |
| `LOCAL_ACQUISITION_BASE` | Local acquisition directory | "results/plant_acquisition" |
| `LOCAL_PLY_TARGET` | Target directory for PLY files | "results/pointclouds" |
| `ROMI_CONFIG` | Path to ROMI Plant-3D-Vision pipeline configuration file | "~/plant-3d-vision/configs/geom_pipe_real.toml" | - |

## Example Configuration

Below is an example of a complete `config.json` file:

```json
{
    "TARGET_POINT": [0.375, 0.35, 0.30],
    "CENTER_POINT": [0.375, 0.35, 0.00],
    "CIRCLE_RADIUS": 0.30,
    "NUM_POSITIONS": 80,
    "Z_OFFSET": 0.20,
    "ARDUINO_PORT": "/dev/ttyACM0",
    "CNC_SPEED": 0.1,
    "UPDATE_INTERVAL": 0.1,
    "STABILIZATION_TIME": 3.0,
    "RESULTS_DIR": "results",
    "ACQUISITION_DIR": "plant_acquisition",
    "TARGETING_DIR": "leaf_targeting",
    "SSH_HOST": "10.0.7.22",
    "SSH_USER": "ayman",
    "KEY_PATH": "/home/romi/.ssh/id_rsa",
    "REMOTE_WORK_PATH": "/mnt/diskSustainability/Scanner_Data/scanner_lyon/3dt_colA/Col_A_2021-01-29/",
    "LOCAL_ACQUISITION_BASE": "results/plant_acquisition",
    "LOCAL_PLY_TARGET": "results/pointclouds",
    "ROMI_CONFIG": "~/plant-3d-vision/configs/geom_pipe_real.toml"
}
```

## ROMI Configuration

The `ROMI_CONFIG` parameter points to a [Plant-3D-Vision](https://github.com/romi/plant-3d-vision) configuration file that defines the 3D reconstruction pipeline. This TOML file controls how the plant point cloud is generated from the acquired images.

Important Plant-3D-Vision settings:

- `Colmap`: Settings for Structure from Motion
- `PointCloud`: Settings for point cloud generation
- `Voxels`: Settings for voxelization
- `TreeGraph`: Settings for skeletonization

For detailed documentation on these settings, refer to the [Plant-3D-Vision repository](https://github.com/romi/plant-3d-vision).

## Recommendations

### Image Acquisition

- For large plants: `CIRCLE_RADIUS` = 0.4-0.5 m
- For small plants: `CIRCLE_RADIUS` = 0.2-0.3 m
- Recommended number of positions: 60-120 depending on plant complexity
- Two circles recommended for plants with complex structures

### Leaf Targeting

- Recommended distance to leaves: 0.3-0.5 m
- Louvain coefficient: 0.3-0.7 (lower values = more communities detected)
- Scale factor should match your point cloud's original units (typically 0.001 for mm → m)

### Hardware Settings

- `STABILIZATION_TIME`: Increase to 5.0s for higher quality photos
- `CNC_SPEED`: Reduce to 0.05 m/s for more stable movements
- `UPDATE_INTERVAL`: Reduce to 0.05s for more responsive feedback during manual control

## Environment-Specific Configurations

For different environments or use cases, you might want to adjust your configuration. Here are some examples:

### Laboratory Setup

```json
{
    "CIRCLE_RADIUS": 0.25,
    "NUM_POSITIONS": 100,
    "CNC_SPEED": 0.05,
    "STABILIZATION_TIME": 5.0
}
```

### Field Setup

```json
{
    "CIRCLE_RADIUS": 0.40,
    "NUM_POSITIONS": 60,
    "CNC_SPEED": 0.1,
    "STABILIZATION_TIME": 2.0
}
```
