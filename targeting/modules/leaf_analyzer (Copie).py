#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Leaf detection — graph-based clustering, fully ARM-compatible.
Remplace open3d KDTree par scipy.spatial.cKDTree (ARM-safe).
"""

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import time
import numpy as np
import open3d
from scipy.sparse import lil_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from targeting.modules.seg_cov import get_labels


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Background separation
# ─────────────────────────────────────────────────────────────────────────────

def separate_plant_from_background(pcd, points, k_kmeans=3):
    """
    KMeans 3D sur coordonnees normalisees — ARM-safe, pas d'eigh.
    Le plus grand cluster = plante.
    pcd/points en metres, get_labels attend du mm → pcd_mm temporaire.
    """
    print(f"  Separating plant from background "
          f"({len(points)} points, k={k_kmeans})...")
    t0 = time.time()

    pcd_mm = open3d.geometry.PointCloud()
    pcd_mm.points = open3d.utility.Vector3dVector(points * 1000.0)

    labels = get_labels(pcd_mm, k=k_kmeans)

    counts = np.bincount(labels)
    largest_label = np.argmax(counts)
    print(f"  Done in {time.time()-t0:.1f}s — cluster sizes: {counts.tolist()}")
    print(f"  Keeping cluster {largest_label} as plant ({counts[largest_label]} pts)")

    mask = labels == largest_label
    return points[mask], np.where(mask)[0]


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — KNN graph + connected components (scipy cKDTree — ARM-safe)
# ─────────────────────────────────────────────────────────────────────────────

def cluster_by_graph(plant_points, k_neighbors=150, max_distance=0.002):
    """
    Graphe KNN symetrique via scipy.spatial.cKDTree + composantes connexes.
    Remplace open3d KDTreeFlann qui segfault sur ARM (open3d 0.18 / Pi OS).
    """
    n = len(plant_points)
    print(f"  Building KNN graph ({n} pts, k={k_neighbors}, "
          f"max_d={max_distance*1000:.1f} mm)...")
    t0 = time.time()

    tree = cKDTree(plant_points)

    # query_ball_point retourne pour chaque point ses voisins dans max_distance
    # Plus efficace que KNN + filtre distance pour ce cas d'usage
    neighbors = tree.query_ball_point(plant_points, r=max_distance, workers=-1)

    adj = lil_matrix((n, n), dtype=np.uint8)
    for i, neigh in enumerate(neighbors):
        for j in neigh:
            if j != i:
                adj[i, j] = 1
                adj[j, i] = 1

    print(f"  Graph built in {time.time()-t0:.1f}s")
    n_clusters, labels = connected_components(adj, directed=False)

    counts = np.bincount(labels)
    top    = np.argsort(counts)[::-1][:10]
    print(f"  {n_clusters} components — top sizes: {[counts[c] for c in top]}")

    return labels, n_clusters


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Filter small clusters
# ─────────────────────────────────────────────────────────────────────────────

def filter_small_clusters(plant_points, labels, min_cluster_size=1000):
    counts = np.bincount(labels)
    large  = np.where(counts >= min_cluster_size)[0]
    print(f"  Clusters >= {min_cluster_size} pts: {len(large)} "
          f"(discarding {len(counts)-len(large)})")

    mask            = np.isin(labels, large)
    pts_filtered    = plant_points[mask]
    labels_filtered = labels[mask]

    unique          = np.unique(labels_filtered)
    remap           = {old: new for new, old in enumerate(unique)}
    labels_remapped = np.array([remap[l] for l in labels_filtered])

    print(f"  {len(pts_filtered)} pts kept in {len(unique)} clusters")
    return pts_filtered, labels_remapped


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Centroids and normals via PCA
# (~15-20 appels seulement — pas de risque OpenBLAS)
# ─────────────────────────────────────────────────────────────────────────────

def compute_centroids_and_normals(pts_filtered, labels_remapped):
    n_clusters = labels_remapped.max() + 1
    centroids  = np.zeros((n_clusters, 3))
    normals    = np.zeros((n_clusters, 3))

    for i in range(n_clusters):
        pts   = pts_filtered[labels_remapped == i]
        mean  = np.mean(pts, axis=0)
        dists = np.linalg.norm(pts - mean, axis=1)
        centroids[i] = pts[np.argmin(dists)]

        centered = pts - centroids[i]
        cov      = np.cov(centered.T)
        _, evecs = np.linalg.eigh(cov)
        normal   = evecs[:, 0]
        if normal[2] < 0:
            normal = -normal
        normals[i] = normal

    return centroids, normals


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Merge parallel and spatially close clusters (Union-Find)
# ─────────────────────────────────────────────────────────────────────────────

def merge_parallel_clusters(centroids, normals, labels_remapped, pts_filtered,
                             angle_threshold_deg=15.0, distance_threshold=0.015):
    n          = len(centroids)
    cos_thresh = np.cos(np.radians(angle_threshold_deg))
    parent     = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    for i in range(n):
        for j in range(i + 1, n):
            if np.linalg.norm(centroids[i] - centroids[j]) > distance_threshold:
                continue
            if abs(np.dot(normals[i], normals[j])) >= cos_thresh:
                union(i, j)

    root_map = {}
    new_idx  = 0
    for i in range(n):
        r = find(i)
        if r not in root_map:
            root_map[r] = new_idx
            new_idx += 1

    new_labels    = np.array([root_map[find(l)] for l in labels_remapped])
    n_new         = new_idx
    new_centroids = np.zeros((n_new, 3))
    new_normals   = np.zeros((n_new, 3))

    for i in range(n_new):
        pts   = pts_filtered[new_labels == i]
        mean  = np.mean(pts, axis=0)
        dists = np.linalg.norm(pts - mean, axis=1)
        new_centroids[i] = pts[np.argmin(dists)]

        centered = pts - new_centroids[i]
        cov      = np.cov(centered.T)
        _, evecs = np.linalg.eigh(cov)
        normal   = evecs[:, 0]
        if normal[2] < 0:
            normal = -normal
        new_normals[i] = normal

    print(f"  After merge: {n_new} clusters (was {n})")
    return new_labels, new_centroids, new_normals


# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Build output dicts
# ─────────────────────────────────────────────────────────────────────────────

def _orient_outward(normal, centroid, all_points):
    plant_center    = np.mean(all_points, axis=0)
    plant_center[2] = np.min(all_points[:, 2])
    if np.dot(normal, plant_center - centroid) > 0:
        normal = -normal
    return normal


def _plane_eq(normal, point):
    d = -float(np.dot(normal, point))
    return [float(normal[0]), float(normal[1]), float(normal[2]), d]


def _target_point(centroid, normal, distance):
    return (np.asarray(centroid) + np.asarray(normal) * distance).tolist()


def build_leaves_data(pts_filtered, labels_remapped, centroids, normals,
                      all_points, distance=0.1):
    n_clusters  = labels_remapped.max() + 1
    leaves_data = []

    print(f"\n  Building leaf data — {n_clusters} leaves, "
          f"target distance = {distance*100:.1f} cm")

    for i in range(n_clusters):
        mask            = labels_remapped == i
        cluster_pts     = pts_filtered[mask]
        cluster_indices = np.where(mask)[0].tolist()

        centroid = centroids[i].copy()
        normal   = normals[i].copy()

        n_len = np.linalg.norm(normal)
        if n_len > 1e-6:
            normal = normal / n_len

        normal = _orient_outward(normal, centroid, all_points)

        leaf = {
            "id"            : i + 1,
            "centroid"      : centroid.tolist(),
            "normal"        : normal.tolist(),
            "plane_equation": _plane_eq(normal, centroid),
            "inlier_ratio"  : 1.0,
            "points_indices": cluster_indices,
            "points"        : cluster_pts.tolist(),
            "target_point"  : _target_point(centroid, normal, distance),
        }
        leaves_data.append(leaf)

        print(f"    Leaf {leaf['id']:2d}: {len(cluster_pts):5d} pts | "
              f"centroid={np.round(centroid,3)} | normal={np.round(normal,3)}")

    return leaves_data


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def detect_leaves(pcd, points,
                  k_kmeans=3,
                  k_neighbors=150,
                  max_distance=0.002,
                  min_cluster_size=1000,
                  angle_threshold_deg=15.0,
                  merge_distance_threshold=0.015,
                  distance=0.1):
    """
    Pipeline complet de detection des feuilles.
    100% ARM-compatible — open3d KDTree remplace par scipy cKDTree.
    """
    print("\n" + "="*55)
    print(" Leaf detection  —  graph clustering (ARM-safe)")
    print("="*55)

    print("\n[1/5] Background separation (KMeans)...")
    plant_points, _ = separate_plant_from_background(pcd, points, k_kmeans)

    print("\n[2/5] Graph-based instance clustering (scipy cKDTree)...")
    labels, _ = cluster_by_graph(plant_points, k_neighbors, max_distance)

    print("\n[3/5] Filtering small clusters...")
    pts_filtered, labels_remapped = filter_small_clusters(
        plant_points, labels, min_cluster_size
    )

    if len(pts_filtered) == 0:
        print("WARNING: No clusters survive filtering. "
              "Consider reducing --min_cluster_size.")
        return []

    print("\n[4/5] Computing centroids and normals (PCA)...")
    centroids, normals = compute_centroids_and_normals(pts_filtered, labels_remapped)

    print("\n[5/5] Merging parallel clusters...")
    labels_remapped, centroids, normals = merge_parallel_clusters(
        centroids, normals, labels_remapped, pts_filtered,
        angle_threshold_deg, merge_distance_threshold
    )

    leaves_data = build_leaves_data(
        pts_filtered, labels_remapped, centroids, normals, points, distance
    )

    print(f"\n{'='*55}")
    print(f" Detection complete: {len(leaves_data)} leaves found")
    print(f"{'='*55}\n")
    return leaves_data


# ─────────────────────────────────────────────────────────────────────────────
# Backward-compatibility stubs
# ─────────────────────────────────────────────────────────────────────────────

def calculate_adaptive_radius(points):
    raise DeprecationWarning("Use detect_leaves() instead.")

def build_connectivity_graph(points, radius):
    raise DeprecationWarning("Use detect_leaves() instead.")

def detect_communities_louvain_multiple(graph, resolution, min_size, n_iterations=5):
    raise DeprecationWarning("Use detect_leaves() instead.")

def extract_leaf_data_from_communities(communities, points, min_inlier_ratio=0.7, distance=0.1):
    raise DeprecationWarning("Use detect_leaves() instead.")