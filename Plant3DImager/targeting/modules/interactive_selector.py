# modules/interactive_selector.py
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import os

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

def select_leaf_with_matplotlib(leaves_data, cloud_points, output_dir=None):
    """
    Display numbered leaves and allow multiple selection via terminal
    
    Args:
        leaves_data: List of leaf data
        cloud_points: Complete point cloud points
        output_dir: Output directory for visualizations
    
    Returns:
        List of selected leaves (dictionaries) in specified order
        or empty list if cancelled
    """
    print("\nPreparing leaf visualization...")
    
    # Create 3D figure
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Display complete cloud in black (sampled for performance)
    max_display_points = 5000
    if len(cloud_points) > max_display_points:
        sample_indices = np.random.choice(len(cloud_points), max_display_points, replace=False)
        display_points = cloud_points[sample_indices]
    else:
        display_points = cloud_points
        
    ax.scatter(display_points[:, 0], display_points[:, 1], display_points[:, 2],
              c='black', s=1, alpha=0.4, label='Point cloud')
    
    # Generate distinct colors for leaves
    colors = generate_distinct_colors(len(leaves_data))
    
    # Display each leaf with its ID
    for i, leaf in enumerate(leaves_data):
        # Get points for this leaf (if available)
        if 'points' in leaf:
            leaf_points = np.array(leaf['points'])
            
            # Sample if too many points
            max_leaf_points = 500
            if len(leaf_points) > max_leaf_points:
                sample_indices = np.random.choice(len(leaf_points), max_leaf_points, replace=False)
                leaf_points = leaf_points[sample_indices]
            
            # Display points
            ax.scatter(leaf_points[:, 0], leaf_points[:, 1], leaf_points[:, 2],
                      c=[colors[i]], s=15, label=f'Leaf {leaf["id"]}')
        
        # Display centroid
        centroid = leaf['centroid']
        ax.scatter([centroid[0]], [centroid[1]], [centroid[2]], 
                  c=[colors[i]], s=100, marker='o', edgecolors='black')
        
        # Display normal (as arrow)
        if 'normal' in leaf:
            normal = leaf['normal']
            normal_length = 0.05  # 5 cm
            arrow_end = [
                centroid[0] + normal[0] * normal_length,
                centroid[1] + normal[1] * normal_length,
                centroid[2] + normal[2] * normal_length
            ]
            ax.quiver(centroid[0], centroid[1], centroid[2],
                     normal[0] * normal_length, normal[1] * normal_length, normal[2] * normal_length,
                     color='red', arrow_length_ratio=0.2)
        
        # Add text with ID slightly offset from centroid
        # Calculate offset based on normal to make text visible
        offset = np.array([0, 0, 0.01])  # Base offset (1 cm upward)
        
        # If normal is available, use its orientation to offset perpendicularly
        if 'normal' in leaf:
            normal = np.array(leaf['normal'])
            # Create vector perpendicular to normal
            if abs(normal[0]) > 0.1 or abs(normal[1]) > 0.1:
                # If normal is not vertical, we can easily create perpendicular vector
                perp = np.array([normal[1], -normal[0], 0])
                perp = perp / np.linalg.norm(perp) * 0.01  # Normalize to 1 cm
                offset = perp
            else:
                # If normal is almost vertical, use standard offset
                offset = np.array([0.01, 0.01, 0.01])
        
        # Text position
        text_pos = np.array(centroid) + offset
        
        # Add text
        ax.text(text_pos[0], text_pos[1], text_pos[2], 
               f"{leaf['id']}", fontsize=14, color='black', weight='bold',
               horizontalalignment='center', verticalalignment='center',
               bbox=dict(facecolor='white', alpha=0.7, edgecolor='black', boxstyle='round,pad=0.3'))
    
    # Configure axes
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.set_title('Identified Leaves', fontsize=16)
    
    # CORRECTION: Invert X and Y axes for more intuitive orientation
    # This places (0,0) closer to us
    ax.invert_xaxis()
    ax.invert_yaxis()
    
    # CORRECTION: Adjust view for better orientation
    ax.view_init(elev=20, azim=60)
    
    # Display legend if not too many leaves
    if len(leaves_data) <= 10:
        ax.legend()
    
    # Save image before display
    plt.tight_layout()
    
    if output_dir:
        visualization_path = os.path.join(output_dir, 'leaves_selection.png')
        plt.savefig(visualization_path, dpi=300)
        print(f"Visualization saved to '{visualization_path}'")
    else:
        plt.savefig('leaves_selection.png', dpi=300)
        print("Visualization saved to 'leaves_selection.png'")
    
    # Display figure
    plt.show()
    
    # Display summary table in terminal
    print("\n=== IDENTIFIED LEAVES ===")
    print("ID | Centroid (x, y, z) | Normal (x, y, z)")
    print("-" * 65)
    
    for leaf in leaves_data:
        centroid = leaf['centroid']
        normal = leaf.get('normal', [0, 0, 0])
        print(f"{leaf['id']:2d} | ({centroid[0]:.3f}, {centroid[1]:.3f}, {centroid[2]:.3f}) | "
              f"({normal[0]:.3f}, {normal[1]:.3f}, {normal[2]:.3f})")
    
    # Ask user to select multiple leaves
    while True:
        try:
            selection_input = input("\nEnter leaf numbers to target in desired order (e.g. '1 4 2 8'), or 'q' to quit: ")
            
            if selection_input.lower() == 'q':
                print("Selection cancelled.")
                return []
            
            # Split by spaces and convert to integers
            selected_ids = [int(id_str) for id_str in selection_input.split()]
            
            # Check if all IDs are valid
            leaf_ids = [leaf['id'] for leaf in leaves_data]
            invalid_ids = [id for id in selected_ids if id not in leaf_ids]
            
            if invalid_ids:
                print(f"Error: The following IDs don't exist: {invalid_ids}. Please try again.")
                continue
            
            # Create list of selected leaves in specified order
            selected_leaves = []
            for selected_id in selected_ids:
                for leaf in leaves_data:
                    if leaf['id'] == selected_id:
                        selected_leaves.append(leaf)
                        break
            
            if not selected_leaves:
                print("No valid leaves selected. Please try again.")
                continue
                
            # Display selected leaves in order
            print("\nSelected leaves in order:")
            for i, leaf in enumerate(selected_leaves):
                print(f"{i+1}. Leaf {leaf['id']}")
            
            return selected_leaves
                
        except ValueError:
            print("Error: Invalid format. Please enter integers separated by spaces.")