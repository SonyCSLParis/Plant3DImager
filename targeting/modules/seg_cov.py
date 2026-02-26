#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
seg_cov.py — ARM-compatible, fidele a l'original instance_seg_v2.
Seul changement : search_radius_vector_3d (open3d, segfault ARM)
                → query_ball_point (scipy cKDTree, ARM-safe)
La logique eigenvalue multi-echelle est identique a l'original.
"""

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from scipy.spatial import cKDTree
import open3d
import time


def gets_evs(pts, tree, scale):
    """
    Calcule les valeurs propres de la covariance locale a chaque point,
    en utilisant tous les voisins dans un rayon `scale`.

    Identique a l'original sauf :
      open3d search_radius_vector_3d → scipy cKDTree.query_ball_point
    """
    N = len(pts)
    evs = np.zeros([N, 3])

    # Calculer tous les voisinages en une seule passe (plus efficace)
    neighbors = tree.query_ball_point(pts, r=scale, workers=1)

    for i, idxs in enumerate(neighbors):
        if len(idxs) >= 3:
            c = np.cov(pts[idxs].T)
            evs[i], _ = np.linalg.eigh(c)
        # sinon on laisse [0,0,0]

    return evs


def get_labels(pcd, k=3):
    """
    Segmentation par features eigenvalue multi-echelle → PCA → KMeans.
    Identique a l'original (seg_cov.py), ARM-compatible.

    Args:
        pcd : open3d.geometry.PointCloud (coordonnees en mm)
        k   : nombre de clusters KMeans

    Returns:
        labels : (N,) int array
    """
    pts = np.array(pcd.points)
    print(f"  get_labels: {len(pts)} points, k_kmeans={k}")

    # cKDTree construit une seule fois, reutilise pour les 3 echelles
    tree = cKDTree(pts)

    evs0 = gets_evs(pts, tree, 1.5)   # scale 1.5 mm
    evs1 = gets_evs(pts, tree, 3.0)   # scale 3.0 mm
    evs2 = gets_evs(pts, tree, 6.0)   # scale 6.0 mm

    s0 = evs0.sum(axis=1)
    s1 = evs1.sum(axis=1)
    s2 = evs2.sum(axis=1)

    # Eviter division par zero
    s0[s0 == 0] = 1.0
    s1[s1 == 0] = 1.0
    s2[s2 == 0] = 1.0

    fs = np.array([
        evs0[:, 0]/s0, evs0[:, 1]/s0, evs0[:, 2]/s0,
        evs1[:, 0]/s1, evs1[:, 1]/s1, evs1[:, 2]/s1,
        evs2[:, 0]/s2, evs2[:, 1]/s2, evs2[:, 2]/s2,
    ]).T    # (N, 9)

    pca = PCA(n_components=3)
    res = pca.fit_transform(fs)

    est = KMeans(init='k-means++', n_clusters=k, n_init=100, random_state=42)
    est.fit(res)

    return est.labels_


def plot3D(pcd, centroids=None, normals=None, normal_length=5.0):
    import plotly.graph_objects as go

    pts  = np.asarray(pcd.points)
    cols = np.asarray(pcd.colors)

    data = [go.Scatter3d(
        x=pts[:, 0], y=pts[:, 1], z=pts[:, 2],
        mode='markers',
        marker=dict(
            size=.4,
            color=['rgb({},{},{})'.format(
                int(c[0]*255), int(c[1]*255), int(c[2]*255)) for c in cols],
        ),
        name='Points'
    )]

    if centroids is not None:
        data.append(go.Scatter3d(
            x=centroids[:, 0], y=centroids[:, 1], z=centroids[:, 2],
            mode='markers',
            marker=dict(size=12, color='red', symbol='diamond'),
            name='Centroids'
        ))

    if centroids is not None and normals is not None:
        for i in range(len(centroids)):
            start = centroids[i]
            end   = centroids[i] + normals[i] * normal_length
            data.append(go.Scatter3d(
                x=[start[0], end[0]],
                y=[start[1], end[1]],
                z=[start[2], end[2]],
                mode='lines',
                line=dict(color='black', width=10),
                showlegend=(i == 0),
                name='Normals' if i == 0 else None
            ))

    fig = go.Figure(data=data)
    fig.update_layout(
        width=1400, height=1000,
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            aspectmode='data',
        ),
        margin=dict(l=0, r=0, t=0, b=0),
    )
    fig.show()


if __name__ == "__main__":
    t0  = time.time()
    pcd = open3d.io.read_point_cloud("pointcloud.ply")
    k   = 3
    labels = get_labels(pcd, k=k)
    counts = np.bincount(labels)
    print(f"Cluster sizes: {counts.tolist()}")
    colors = np.array([
        [0.9, 0.2, 0.2],
        [0.2, 0.4, 0.9],
        [0.6, 0.6, 0.6],
    ])
    pcd.colors = open3d.utility.Vector3dVector(colors[labels])
    plot3D(pcd)
    print(f"Duree: {time.time()-t0:.1f}s")