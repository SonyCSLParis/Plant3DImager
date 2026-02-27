# User Guide

This guide details the usage procedures for each operating mode of the system.

## 1. Circular Image Acquisition

The image acquisition allows photographing a plant along a circular path.

### Acquisition Parameters

- `--circles` : Number of circles (1 or 2)
- `--positions` : Number of positions per circle
- `--radius` : Circle radius in meters
- `--z_offset` : Z offset between two circles (if circles=2)

### Acquisition Procedure

1. Position the plant at the center of the system (point defined in config.json)
2. Launch the acquisition command: `python main.py --mode acquisition`
3. The robot will initialize and then ask for confirmation
4. After confirmation, the robot will follow the circle(s) taking photos
5. Images and metadata will be saved in the `results/plant_acquisition/` folder

## 2. Leaf Targeting

Targeting allows analyzing a 3D point cloud of the plant and photographing individual leaves.

### Targeting Parameters

- `--point_cloud` : Path to the PLY point cloud file
- `--scale` : Scale factor (0.001 for mm -> m)
- `--distance` : Distance to target leaves in meters
- `--louvain_coeff` : Coefficient for detection algorithm (0.5 recommended)

### Targeting Procedure

1. Generate a point cloud via acquisition and synchronization
2. Launch the targeting command: `python main.py --mode targeting --point_cloud path/to/PointCloud.ply`
3. A visualization of detected leaves will be displayed
4. Select the leaves to target by entering their numbers
5. The robot will move to each leaf and take photos
6. Images will be saved in `results/leaf_targeting/`

## 3. Manual Control

Manual mode allows directly controlling robot movements and photo taking.

### Manual Mode Commands

- Format: `x y z [pan] [tilt] [photo]`
  - `x y z` : Coordinates in meters
  - `pan tilt` : Camera angles in degrees (optional)
  - `photo` : 1 to take a photo, 0 or omitted to not take a photo

### Usage Example

```
Command > 0.3 0.4 0.2
Command > 0.3 0.4 0.2 45 30
Command > 0.3 0.4 0.2 45 30 1
Command > help
Command > q
```

## 4. Server Synchronization

The synchronization module handles data transfer with the server for 3D processing using the ROMI Plant-3D-Vision pipeline.

### Synchronization Parameters

- `--ssh-host` : SSH server address
- `--ssh-user` : SSH username
- `--key-path` : Path to SSH key
- `--remote-path` : Path to remote working directory
- `--dry-run` : Simulation mode (no actual execution)

### Synchronization Procedure

1. Launch the sync command: `python main.py --mode sync`
2. The system will:
   - Clean the server directory
   - Upload acquisition data
   - Run the Plant-3D-Vision pipeline on the server using `romi_run_task`
   - Download the generated point cloud
3. The point cloud will be saved in `results/pointclouds/`

### ROMI Pipeline Tasks

The synchronization executes the following ROMI tasks on the server:

1. `Clean` - Prepares the workspace
2. `PointCloud` - Processes images to generate a 3D point cloud

These tasks are executed using the ROMI configuration specified in `config.json` (`ROMI_CONFIG` parameter).

## 5. Complete Workflow

Workflow mode automatically executes the entire process: acquisition, synchronization, and targeting.

### Workflow Parameters

- `--skip-acquisition` : Skip acquisition step
- `--skip-sync` : Skip synchronization step
- `--skip-targeting` : Skip targeting step
- `--point-cloud` : Path to an existing point cloud (if --skip-sync)

### Workflow Procedure

1. Position the plant at the center of the system
2. Launch the command: `python main.py --mode workflow`
3. The system will sequentially perform:
   - Circular image acquisition
   - Server synchronization
   - Point cloud processing
   - Leaf targeting and photography
4. All results will be saved in their respective folders

## Troubleshooting

### Common Issues

1. **Arduino connection error**
   - Check if the Arduino is properly connected
   - Verify the port in config.json (`ARDUINO_PORT`)

2. **CNC movement issues**
   - Ensure the CNC is powered and initialized
   - Check for any physical obstructions
   - Try reducing speed (`--speed` parameter)

3. **Server synchronization failures**
   - Verify SSH credentials and connectivity
   - Check if the remote path exists
   - Look for database locks on the server

4. **Leaf detection problems**
   - Try adjusting the Louvain coefficient (`--louvain_coeff`)
   - Check the scale factor (`--scale`)
   - Ensure the point cloud quality is sufficient
