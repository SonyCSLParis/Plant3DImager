# modules/visualization.py
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import os
from core.utils import config

# Cylinder parameters for visualization
CYLINDER_CENTER = (config.CENTER_POINT[0], config.CENTER_POINT[1])
CYLINDER_RADIUS = 0.15  # 15cm radius
CYLINDER_Z_MIN = -0.315
CYLINDER_Z_MAX = 0.0

def generate_distinct_colors(n):
    """Generate n distinct colors"""
    colors = []
    for i in range(n):
        hue = i / n
        saturation = 0.7 + 0.3 * (i % 2)
        value = 0.8 + 0.2 * (i % 3)
        
        # Convert HSV to RGB using colorsys (safer)
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        
        # Ensure values are in [0, 1]
        r = max(0.0, min(1.0, r))
        g = max(0.0, min(1.0, g))
        b = max(0.0, min(1.0, b))
            
        colors.append([r, g, b])
    return colors

def visualize_path(path, cloud_points=None, leaf_points=None, leaf_normal=None, output_dir=None):
    """Visualize planned trajectory"""
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
    """Visualize complete trajectory with cylinder avoidance zone"""
    # Extract positions
    positions = [np.array(point_info["position"]) for point_info in path]
    
    # === CREATE DUAL PLOT: 3D + TOP VIEW ===
    fig = plt.figure(figsize=(16, 8))
    
    # --- 3D VIEW ---
    ax1 = fig.add_subplot(121, projection='3d')
    
    # Cylinder 3D
    theta = np.linspace(0, 2*np.pi, 50)
    for i in range(0, 50, 2):
        cx = CYLINDER_CENTER[0] + CYLINDER_RADIUS * np.cos(theta[i])
        cy = CYLINDER_CENTER[1] + CYLINDER_RADIUS * np.sin(theta[i])
        ax1.plot([cx, cx], [cy, cy], [CYLINDER_Z_MIN, CYLINDER_Z_MAX], 'r-', linewidth=3, alpha=0.8)
    
    cylinder_x = CYLINDER_CENTER[0] + CYLINDER_RADIUS * np.cos(theta)
    cylinder_y = CYLINDER_CENTER[1] + CYLINDER_RADIUS * np.sin(theta)
    
    ax1.plot(cylinder_x, cylinder_y, CYLINDER_Z_MIN, 'r-', linewidth=4, label=f'Avoidance cylinder (r={CYLINDER_RADIUS}m)')
    ax1.plot(cylinder_x, cylinder_y, CYLINDER_Z_MAX, 'r-', linewidth=4)
    
    # Trajectory 3D
    ax1.plot([p[0] for p in positions], [p[1] for p in positions], [p[2] for p in positions], 
            'b-', linewidth=2, label="Curved trajectory")
    
    # Point cloud 3D
    if cloud_points is not None:
        if len(cloud_points) > 2000:
            sample_indices = np.random.choice(len(cloud_points), 2000, replace=False)
            display_points = cloud_points[sample_indices]
        else:
            display_points = cloud_points
        ax1.scatter(display_points[:, 0], display_points[:, 1], display_points[:, 2],
                  c='black', s=0.5, alpha=0.3)
    
    # Path points 3D
    for position, point_info in zip(positions, path):
        if point_info["type"] == "photo_point":
            ax1.scatter(position[0], position[1], position[2], color='blue', s=100, marker='s')
        elif point_info["type"] == "fluoro_point":
            ax1.scatter(position[0], position[1], position[2], color='red', s=100, marker='*')
    
    ax1.set_xlabel('X (m)')
    ax1.set_ylabel('Y (m)')
    ax1.set_zlabel('Z (m)')
    ax1.set_title('3D View with Cylinder Avoidance')
    ax1.view_init(elev=25, azim=45)
    ax1.legend()
    
    # --- TOP VIEW (2D) ---
    ax2 = fig.add_subplot(122)
    
    # Cylinder top view (circle)
    circle = plt.Circle(CYLINDER_CENTER, CYLINDER_RADIUS, color='red', fill=False, linewidth=3, label=f'Cylinder (r={CYLINDER_RADIUS}m)')
    ax2.add_patch(circle)
    
    # Trajectory top view
    ax2.plot([p[0] for p in positions], [p[1] for p in positions], 'b-', linewidth=2, label="Trajectory (XY projection)")
    
    # Point cloud top view
    if cloud_points is not None:
        if len(cloud_points) > 3000:
            sample_indices = np.random.choice(len(cloud_points), 3000, replace=False)
            display_points = cloud_points[sample_indices]
        else:
            display_points = cloud_points
        ax2.scatter(display_points[:, 0], display_points[:, 1], c='gray', s=0.5, alpha=0.2)
    
    # Path points top view
    target_count = 0
    for position, point_info in zip(positions, path):
        if point_info["type"] == "photo_point":
            ax2.scatter(position[0], position[1], color='blue', s=100, marker='s')
        elif point_info["type"] == "fluoro_point":
            target_count += 1
            ax2.scatter(position[0], position[1], color='red', s=100, marker='*')
            ax2.text(position[0] + 0.01, position[1] + 0.01, f"{target_count}", fontsize=10)
        elif point_info["type"] == "start":
            ax2.scatter(position[0], position[1], color='purple', s=120, marker='D')
    
    ax2.set_xlabel('X (m)')
    ax2.set_ylabel('Y (m)')
    ax2.set_title('Top View - Avoidance Strategy')
    ax2.grid(True, alpha=0.3)
    ax2.axis('equal')
    ax2.legend()
    
    # Add algorithm explanation as text
    explanation = """AVOIDANCE ALGORITHM:
1. Sample 100 points along direct line
2. Check intersection with cylinder
3. If intersect: calculate tangent points
4. Generate Bézier curve around cylinder
5. Sample curved waypoints"""
    
    ax2.text(0.02, 0.98, explanation, transform=ax2.transAxes, fontsize=9, 
             verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8))
    
    plt.tight_layout()
    
    if output_dir:
        visualization_path = os.path.join(output_dir, 'complete_path_dual.png')
        plt.savefig(visualization_path, dpi=300, bbox_inches='tight')
        print(f"Dual visualization saved to '{visualization_path}'")
    
    plt.show()