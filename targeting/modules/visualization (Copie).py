# modules/visualization.py
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import os

def visualize_path(path, cloud_points=None, leaf_points=None, leaf_normal=None, output_dir=None):
    """
    Visualize planned trajectory
    
    Args:
        path: List of dictionaries describing the trajectory
        cloud_points: Point cloud points (optional)
        leaf_points: Leaf points (optional)
        leaf_normal: Leaf normal (optional)
        output_dir: Output directory for visualizations
    """
    # Extract positions
    positions = [np.array(point_info["position"]) for point_info in path]
    
    # Create figure
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Display cloud if available
    if cloud_points is not None:
        # Sample for performance
        max_display_points = 5000
        if len(cloud_points) > max_display_points:
            sample_indices = np.random.choice(len(cloud_points), max_display_points, replace=False)
            display_points = cloud_points[sample_indices]
        else:
            display_points = cloud_points
            
        ax.scatter(display_points[:, 0], display_points[:, 1], display_points[:, 2],
                  c='black', s=1, alpha=0.4, label='Point cloud')
    
    # Display leaf if available
    if leaf_points is not None:
        # Sample if needed
        max_leaf_points = 500
        if len(leaf_points) > max_leaf_points:
            sample_indices = np.random.choice(len(leaf_points), max_leaf_points, replace=False)
            display_leaf_points = leaf_points[sample_indices]
        else:
            display_leaf_points = leaf_points
            
        ax.scatter(display_leaf_points[:, 0], display_leaf_points[:, 1], display_leaf_points[:, 2],
                  c='green', s=15, label='Leaf')
    
    # Display normal if available
    if leaf_normal is not None and leaf_points is not None:
        # Calculate centroid
        centroid = np.mean(leaf_points, axis=0)
        
        # Arrow length
        normal_length = 0.10  # 10 cm
        
        # Display normal
        ax.quiver(centroid[0], centroid[1], centroid[2],
                 leaf_normal[0] * normal_length, 
                 leaf_normal[1] * normal_length,
                 leaf_normal[2] * normal_length,
                 color='red', arrow_length_ratio=0.2, linewidth=2,
                 label='Normal')
    
    # Display trajectory points with legend for each type
    point_types = {'start': ('Start', 'blue', 'o', 100),
                  'via_point': ('Intermediate point', 'orange', 's', 100),
                  'target': ('Target point', 'red', '*', 150),
                  'end': ('Final position', 'purple', 'D', 150)}
    
    # Track types already added to legend
    legend_added = set()
    
    for i, (position, point_info) in enumerate(zip(positions, path)):
        point_type = point_info["type"]
        
        # Get style information for this point type
        if point_type in point_types:
            label, color, marker, size = point_types[point_type]
        else:
            # Default type if not recognized
            label, color, marker, size = ('Point', 'gray', 'o', 80)
        
        # Add to legend only first time for this type
        if point_type not in legend_added:
            ax.scatter([position[0]], [position[1]], [position[2]],
                      c=color, s=size, marker=marker, label=label)
            legend_added.add(point_type)
        else:
            ax.scatter([position[0]], [position[1]], [position[2]],
                      c=color, s=size, marker=marker)
    
    # Display trajectory as a line
    path_array = np.array(positions)
    ax.plot(path_array[:, 0], path_array[:, 1], path_array[:, 2],
           'k--', linewidth=2, label='Trajectory')
    
    # Configure axes
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.set_title('Planned trajectory', fontsize=16)
    
    # CORRECTION: Invert X and Y axes for more intuitive orientation
    # This places (0,0) closer to us
    ax.invert_xaxis()
    ax.invert_yaxis()
    
    # CORRECTION: Adjust view for better orientation
    ax.view_init(elev=20, azim=60)
    
    # Legend
    ax.legend()
    
    # Save and display
    plt.tight_layout()
    
    if output_dir:
        visualization_path = os.path.join(output_dir, 'planned_path.png')
        plt.savefig(visualization_path, dpi=300)
        print(f"Trajectory visualization saved to '{visualization_path}'")
    else:
        plt.savefig('planned_path.png', dpi=300)
        print("Trajectory visualization saved to 'planned_path.png'")
        
    plt.show()

def visualize_complete_path(path, cloud_points=None, leaves_points=None, leaves_normals=None, output_dir=None):
    """
    Visualize a complete trajectory visiting multiple leaves
    
    Args:
        path: List of dictionaries describing the trajectory
        cloud_points: Point cloud points (optional)
        leaves_points: List of leaf points (optional)
        leaves_normals: List of leaf normals (optional)
        output_dir: Output directory for visualizations
    """
    # Extract positions
    positions = [np.array(point_info["position"]) for point_info in path]
    
    # Create figure
    fig = plt.figure(figsize=(14, 12))
    ax = fig.add_subplot(111, projection='3d')
    
    # Display cloud if available
    if cloud_points is not None:
        # Sample for performance
        max_display_points = 5000
        if len(cloud_points) > max_display_points:
            sample_indices = np.random.choice(len(cloud_points), max_display_points, replace=False)
            display_points = cloud_points[sample_indices]
        else:
            display_points = cloud_points
            
        ax.scatter(display_points[:, 0], display_points[:, 1], display_points[:, 2],
                  c='black', s=1, alpha=0.3, label='Point cloud')
    
    # Display leaves if available
    if leaves_points is not None:
        # Generate distinct colors for leaves
        n_leaves = len(leaves_points)
        import colorsys
        
        colors = []
        for i in range(n_leaves):
            hue = i / n_leaves
            saturation = 0.7
            value = 0.8
            r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
            colors.append([r, g, b])
        
        for i, leaf_points in enumerate(leaves_points):
            # Sample if needed
            max_leaf_points = 500
            if len(leaf_points) > max_leaf_points:
                sample_indices = np.random.choice(len(leaf_points), max_leaf_points, replace=False)
                display_leaf_points = leaf_points[sample_indices]
            else:
                display_leaf_points = leaf_points
                
            ax.scatter(display_leaf_points[:, 0], display_leaf_points[:, 1], display_leaf_points[:, 2],
                      c=[colors[i]], s=15, label=f'Leaf {i+1}')
            
            # Display normal if available
            if leaves_normals is not None and i < len(leaves_normals):
                leaf_normal = leaves_normals[i]
                # Calculate centroid
                centroid = np.mean(leaf_points, axis=0)
                
                # Arrow length
                normal_length = 0.10  # 10 cm
                
                # Display normal
                ax.quiver(centroid[0], centroid[1], centroid[2],
                         leaf_normal[0] * normal_length, 
                         leaf_normal[1] * normal_length,
                         leaf_normal[2] * normal_length,
                         color='red', arrow_length_ratio=0.2, linewidth=2)
    
    # Display trajectory points with legend for each type
    point_types = {'start': ('Start', 'blue', 'o', 100),
                  'via_point': ('Intermediate point', 'orange', 's', 50),
                  'target': ('Target point', 'red', '*', 150),
                  'end': ('Final position', 'purple', 'D', 150)}
    
    # Track types already added to legend
    legend_added = set()
    
    # Annotate target points with their order number
    target_count = 0
    
    for i, (position, point_info) in enumerate(zip(positions, path)):
        point_type = point_info["type"]
        
        # Get style information for this point type
        if point_type in point_types:
            label, color, marker, size = point_types[point_type]
        else:
            # Default type if not recognized
            label, color, marker, size = ('Point', 'gray', 'o', 80)
        
        # Add to legend only first time for this type
        if point_type not in legend_added:
            ax.scatter([position[0]], [position[1]], [position[2]],
                      c=color, s=size, marker=marker, label=label)
            legend_added.add(point_type)
        else:
            ax.scatter([position[0]], [position[1]], [position[2]],
                      c=color, s=size, marker=marker)
        
        # Add number for target points
        if point_type == "target":
            target_count += 1
            ax.text(position[0], position[1], position[2] + 0.01,
                   f"{target_count}", fontsize=12, color='black',
                   horizontalalignment='center', verticalalignment='center',
                   bbox=dict(facecolor='white', alpha=0.7, edgecolor='black'))
    
    # Display trajectory as a line
    path_array = np.array(positions)
    ax.plot(path_array[:, 0], path_array[:, 1], path_array[:, 2],
           'k--', linewidth=2, label='Trajectory')
    
    # Configure axes
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.set_title('Complete planned trajectory', fontsize=16)
    
    # Invert X and Y axes for more intuitive orientation
    ax.invert_xaxis()
    ax.invert_yaxis()
    
    # Adjust view for better orientation
    ax.view_init(elev=20, azim=60)
    
    # Legend
    ax.legend()
    
    # Save and display
    plt.tight_layout()
    
    if output_dir:
        visualization_path = os.path.join(output_dir, 'complete_path.png')
        plt.savefig(visualization_path, dpi=300)
        print(f"Complete trajectory visualization saved to '{visualization_path}'")
    else:
        plt.savefig('complete_path.png', dpi=300)
        print("Complete trajectory visualization saved to 'complete_path.png'")
        
    plt.show()