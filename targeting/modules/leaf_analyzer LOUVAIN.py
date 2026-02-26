# modules/leaf_analyzer.py
import numpy as np
import open3d as o3d
from scipy.spatial import cKDTree
import networkx as nx
import random
import time

try:
    import community as community_louvain
    LOUVAIN_AVAILABLE = True
except ImportError:
    LOUVAIN_AVAILABLE = False
    print("ERROR: 'python-louvain' package is not installed.")
    print("To install: pip install python-louvain")

def calculate_adaptive_radius(points):
    """
    Calculate adaptive connectivity radius
    """
    if len(points) < 10:
        return 0.01
    
    # Sample to speed up calculation
    sample_size = min(1000, len(points))
    sample_indices = np.random.choice(len(points), sample_size, replace=False)
    sample_points = points[sample_indices]
    
    # Create KDTree on ALL original points
    full_tree = cKDTree(points)
    
    # For each sampled point, find its nearest neighbor
    all_distances = []
    for point in sample_points:
        # Find 2 nearest neighbors (first being the point itself)
        distances, _ = full_tree.query(point, k=2)
        # Ignore self-distance (first distance = 0)
        neighbor_distance = distances[1]
        all_distances.append(neighbor_distance)
    
    # Calculate average distance to first nearest neighbor
    avg_1nn = np.mean(all_distances)
    
    # Adaptive radius: 5x average distance to nearest neighbor
    adaptive_radius = avg_1nn * 5.0
    
    print(f"1st neighbor distance: {avg_1nn*1000:.2f} mm")
    print(f"Adaptive radius: {adaptive_radius*1000:.2f} mm")
    
    return adaptive_radius

def calculate_auto_louvain_coefficient(points):
    """
    Calculate automatic Louvain coefficient based on density
    Adapted from alpha_louvain_interactive.py
    """
    # Calculate bounding box volume
    min_bound = np.min(points, axis=0)
    max_bound = np.max(points, axis=0)
    dimensions = max_bound - min_bound
    volume = np.prod(dimensions)
    
    # Calculate density (points per m³)
    density = len(points) / volume if volume > 0 else 1
    
    # Coefficient based on log10 of density divided by 2
    auto_coeff = max(0.1, np.log10(density) / 2)
    
    print(f"Points: {len(points)}")
    print(f"Volume: {volume:.6f} m³")
    print(f"Density: {density:.2f} points/m³")
    print(f"Auto coefficient: {auto_coeff:.2f}")
    
    return auto_coeff

def build_connectivity_graph(points, radius):
    """
    Build connectivity graph
    Adapted from alpha_louvain_interactive.py
    """
    start_time = time.time()
    
    # Create empty graph
    graph = nx.Graph()
    
    # Add nodes (one per point)
    for i in range(len(points)):
        graph.add_node(i)
    
    # Use KDTree for efficient neighbor search
    tree = cKDTree(points)
    
    # For each point, find neighbors within specified radius
    for i in range(len(points)):
        # Find indices of neighbors
        indices = tree.query_ball_point(points[i], radius)
        
        # Add edges to neighbors
        for j in indices:
            if i < j:  # To avoid duplicates
                # Calculate Euclidean distance
                dist = np.linalg.norm(points[i] - points[j])
                
                # Weight is inverse of distance
                weight = 1.0 / max(dist, 1e-6)
                
                graph.add_edge(i, j, weight=weight)
        
        # Display progress
        if i % 5000 == 0 or i == len(points) - 1:
            print(f"  Progress: {i+1}/{len(points)} points")
    
    print(f"Graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    print(f"Time: {time.time() - start_time:.2f}s")
    
    return graph

def detect_communities_louvain_multiple(graph, resolution, min_size, n_iterations=5):
    """
    Detect communities with randomized Louvain
    Adapted from alpha_louvain_interactive.py
    """
    if not LOUVAIN_AVAILABLE:
        print("Error: python-louvain module not available")
        return []
        
    if n_iterations <= 0:
        print("ERROR: Number of iterations must be positive.")
        return []
    
    best_partition = None
    best_modularity = -1
    best_communities = []
    
    print(f"Running Louvain {n_iterations} times with random order...")
    
    # Create copy of graph to avoid modifying it
    graph_copy = graph.copy()
    
    for i in range(n_iterations):
        start_time = time.time()
        
        # Randomly reorder nodes
        shuffled_nodes = list(graph_copy.nodes())
        random.shuffle(shuffled_nodes)
        
        # Create mapping dictionary
        node_map = {old: new for new, old in enumerate(shuffled_nodes)}
        reverse_map = {new: old for new, old in enumerate(shuffled_nodes)}
        
        # Create new graph with reordered nodes
        shuffled_graph = nx.Graph()
        for old_u, old_v, data in graph_copy.edges(data=True):
            new_u, new_v = node_map[old_u], node_map[old_v]
            shuffled_graph.add_edge(new_u, new_v, **data)
        
        # Run Louvain on reordered graph
        partition = community_louvain.best_partition(shuffled_graph, resolution=resolution)
        
        # Calculate modularity of this partition
        modularity = community_louvain.modularity(partition, shuffled_graph)
        
        # Map partition to original nodes
        original_partition = {reverse_map[node]: comm for node, comm in partition.items()}
        
        # If this is best modularity so far, keep it
        if modularity > best_modularity:
            best_modularity = modularity
            best_partition = original_partition
        
        print(f"  Iteration {i+1}/{n_iterations}: Modularity = {modularity:.4f}, Time = {time.time() - start_time:.2f}s")
    
    print(f"Best modularity: {best_modularity:.4f}")
    
    # Group nodes by community
    communities = {}
    for node, community_id in best_partition.items():
        if community_id not in communities:
            communities[community_id] = set()
        communities[community_id].add(node)
    
    # Filter out communities that are too small
    filtered_communities = [comm for comm in communities.values() if len(comm) >= min_size]
    
    # Sort by decreasing size
    sorted_communities = sorted(filtered_communities, key=len, reverse=True)
    
    print(f"Total communities: {len(communities)}")
    print(f"Communities >= {min_size} points: {len(filtered_communities)}")
    
    # Display statistics about communities
    if sorted_communities:
        print("Top 5 communities:")
        for i, comm in enumerate(sorted_communities[:5]):
            print(f"  {i+1}: {len(comm)} points")
    
    return sorted_communities

def fit_plane_to_points(points, all_points=None, distance_threshold=0.005, ransac_n=3, num_iterations=1000):
    """
    Fit plane to a set of points via RANSAC and orient normal outward
    
    Args:
        points: Community points (leaf)
        all_points: All cloud points (to calculate plant center)
        distance_threshold: Distance threshold for RANSAC
        ransac_n: Number of points for RANSAC
        num_iterations: Number of iterations for RANSAC
        
    Returns:
        Dictionary with plane information
    """
    if len(points) < 3:
        print("Not enough points to fit plane")
        return {
            'normal': np.array([0, 0, 1]),
            'centroid': np.mean(points, axis=0) if len(points) > 0 else np.array([0, 0, 0]),
            'equation': [0, 0, 1, 0],
            'inlier_ratio': 0,
            'inliers': []
        }
    
    # Determine plant center (centroid of all points)
    if all_points is None:
        # If all_points not provided, use XY centroid of points as reference
        # but with minimum Z height
        xy_centroid = np.mean(points[:, :2], axis=0)
        min_z = np.min(points[:, 2])
        plant_center = np.array([xy_centroid[0], xy_centroid[1], min_z])
    else:
        # Use centroid of all points as plant center
        plant_center = np.mean(all_points, axis=0)
    
    # Create Open3D point cloud
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    
    # Estimate normals
    pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.02, max_nn=30))
    
    # Fit plane with RANSAC
    try:
        plane_model, inliers = pcd.segment_plane(distance_threshold=distance_threshold,
                                               ransac_n=ransac_n,
                                               num_iterations=num_iterations)
        
        # Extract plane parameters: ax + by + cz + d = 0
        [a, b, c, d] = plane_model
        
        # Normalize normal vector
        normal = np.array([a, b, c])
        normal_length = np.linalg.norm(normal)
        if normal_length > 0:
            normal = normal / normal_length
        
        # Calculate inlier percentage
        inlier_ratio = len(inliers) / len(points) if len(points) > 0 else 0
        
        # Calculate centroid
        centroid = np.mean(points, axis=0)
        
        # Check normal orientation (to point "outward")
        direction_to_center = plant_center - centroid
        
        # If normal points toward center, invert it
        # Use margin to avoid edge cases
        dot_product = np.dot(normal, direction_to_center)
        if dot_product > 0.1 * np.linalg.norm(direction_to_center):
            normal = -normal
            a, b, c = -a, -b, -c
            d = -d
        
        # Create results dictionary
        plane_info = {
            'normal': normal,
            'centroid': centroid,
            'equation': [a, b, c, d],
            'inlier_ratio': inlier_ratio,
            'inliers': inliers
        }
        
        return plane_info
        
    except Exception as e:
        print(f"Error fitting plane: {e}")
        # Return default normal (upward)
        return {
            'normal': np.array([0, 0, 1]),
            'centroid': np.mean(points, axis=0),
            'equation': [0, 0, 1, 0],
            'inlier_ratio': 0,
            'inliers': []
        }

def calculate_target_point(leaf_data, distance=0.10):
    """
    Calculate target point at given distance from leaf plane
    
    Args:
        leaf_data: Dictionary containing leaf data
        distance: Desired distance from plane (in meters)
    
    Returns:
        Target point coordinates [x, y, z]
    """
    centroid = np.array(leaf_data['centroid'])
    normal = np.array(leaf_data['normal'])
    
    # Calculate target point by following normal
    target_point = centroid + normal * distance
    
    return target_point.tolist()

def extract_leaf_data_from_communities(communities, points, min_inlier_ratio=0.7, distance=0.1):
    """
    Extract leaf data from detected communities
    
    Args:
        communities: List of communities (sets of indices)
        points: Complete point cloud
        min_inlier_ratio: Minimum inlier ratio to consider surface valid
        distance: Distance to leaves in meters for target point calculation
    
    Returns:
        List of leaf data in standardized format
    """
    leaves_data = []
    
    # Calculate approximate plant center
    plant_center = np.mean(points, axis=0)
    # Use minimum height for center (plant base)
    plant_center[2] = np.min(points[:, 2])
    
    print(f"\nUsing distance of {distance*100:.1f} cm for target point calculation")
    
    for i, community in enumerate(communities):
        # Extract points for this community
        comm_indices = list(community)
        comm_points = points[comm_indices]
        
        # Calculate centroid
        centroid = np.mean(comm_points, axis=0)
        
        # Fit plane to community passing all points
        plane_info = fit_plane_to_points(comm_points, points)
        
        # Check if plane is good quality
        if plane_info['inlier_ratio'] < min_inlier_ratio:
            print(f"Community {i+1}: Inlier ratio too low ({plane_info['inlier_ratio']:.2f})")
            continue
        
        # Double-check normal orientation outward
        direction_to_center = plant_center - centroid
        dot_product = np.dot(plane_info['normal'], direction_to_center)
        if dot_product > 0:
            # Normal still points toward center - invert it
            normal = -np.array(plane_info['normal'])
            plane_info['normal'] = normal
            # Also invert plane equation
            a, b, c, d = plane_info['equation']
            plane_info['equation'] = [-a, -b, -c, -d]
            print(f"Community {i+1}: Normal reoriented outward")
        
        # Calculate target point at specified distance from leaf
        target_point = calculate_target_point(plane_info, distance=distance)
        
        # Create entry for this leaf
        leaf_data = {
            "id": i + 1,  # ID starting at 1
            "centroid": centroid.tolist(),
            "normal": plane_info["normal"].tolist(),
            "plane_equation": plane_info["equation"],
            "inlier_ratio": plane_info["inlier_ratio"],
            "points_indices": comm_indices,
            "points": comm_points.tolist(),
            "target_point": target_point
        }
        
        leaves_data.append(leaf_data)
    
    print(f"Extracted leaves: {len(leaves_data)}")
    return leaves_data