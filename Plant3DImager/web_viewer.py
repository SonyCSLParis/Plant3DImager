#!/usr/bin/env python3
import dash
from dash import html, dcc, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
import plotly.express as px
import json
import numpy as np
import os
from pathlib import Path
import base64
import time
import glob

app = dash.Dash(__name__)

# Palette segmentation — même ordre que storage_manager.SEG_PALETTE
SEG_PALETTE_HEX = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
    '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
    '#bcbd22', '#17becf', '#39739f', '#ffb347',
    '#5aae61', '#ef4136', '#af76a2', '#a6761d',
    '#cedb9c', '#dcdcdc', '#ffed6f', '#56b4e9',
]

# ─────────────────────────────────────────────────────────────────────────────
# Couleurs basées sur Fv/Fm — gradient noir → jaune
# ─────────────────────────────────────────────────────────────────────────────

def normalize_fvfm(leaves_data, visited_leaves):
    """
    Normalisation min-max des valeurs Fv/Fm des feuilles visitées.
    Retourne dict {leaf_id: valeur normalisée 0→1}.
    Les feuilles sans fvfm ne sont pas incluses.
    """
    values = {}
    for leaf in leaves_data.get('leaves', []):
        if leaf['id'] in visited_leaves and leaf.get('fvfm') is not None:
            values[leaf['id']] = leaf['fvfm']

    if not values:
        return {}

    vmin = min(values.values())
    vmax = max(values.values())

    if vmax == vmin:
        return {lid: 0.5 for lid in values}

    return {lid: (v - vmin) / (vmax - vmin) for lid, v in values.items()}


def fvfm_to_color(normalized):
    """Gradient noir (0) → jaune (1) : RGB (0,0,0) → (255,255,0)"""
    t = max(0.0, min(1.0, normalized))
    r = int(255 * t)
    g = int(255 * t)
    b = 0
    return f'#{r:02x}{g:02x}{b:02x}'

def find_latest_targeting_session():
    """Trouve le répertoire de session de targeting le plus récent"""
    base_pattern = "results/leaf_targeting/leaf_analysis_*"
    session_dirs = glob.glob(base_pattern)
    
    if not session_dirs:
        print("Aucun répertoire de targeting trouvé")
        return None
    
    # Trier par nom (timestamp) décroissant
    session_dirs.sort(reverse=True)
    latest_dir = session_dirs[0]
    print(f"Répertoire de session trouvé: {latest_dir}")
    return Path(latest_dir)

def find_all_targeting_sessions():
    """Trouve tous les répertoires de session de targeting - Format generique (label/value)"""
    base_pattern = "results/leaf_targeting/leaf_analysis_*"
    session_dirs = glob.glob(base_pattern)
    
    if not session_dirs:
        return [{'label': 'No sessions found - run targeting first', 'value': None}]
    
    # Trier par nom (timestamp) décroissant
    session_dirs.sort(reverse=True)
    
    sessions = []
    for session_dir in session_dirs:
        session_path = Path(session_dir)
        
        # Extraire la date du nom du répertoire
        session_name = session_path.name
        try:
            # Format: leaf_analysis_20251211-134611
            date_part = session_name.split('_')[-1]  # 20251211-134611
            date_str = date_part[:8]  # 20251211
            time_str = date_part[9:]  # 134611
            
            # Convertir en format lisible
            from datetime import datetime
            dt = datetime.strptime(f"{date_str}-{time_str}", "%Y%m%d-%H%M%S")
            formatted_date = dt.strftime("%d/%m/%Y à %H:%M:%S")
            
        except:
            formatted_date = session_name
        
        # Compter les feuilles dans la session
        try:
            leaves_file = session_path / "analysis" / "leaves_data.json"
            if leaves_file.exists():
                with open(leaves_file, 'r') as f:
                    leaves_data = json.load(f)
                    leaf_count = len(leaves_data.get('leaves', []))
            else:
                leaf_count = 0
        except:
            leaf_count = 0
            
        # Format compatible generique: label lisible + value = chemin
        display_name = f"{session_name} - {formatted_date} ({leaf_count} feuilles)"
        sessions.append({
            'label': display_name,
            'value': str(session_path)
        })
    
    return sessions if sessions else [{'label': 'No session files found', 'value': None}]

def load_targeting_data(session_dir=None):
    """Charge toutes les données d'une session de targeting"""
    if session_dir is None:
        session_dir = find_latest_targeting_session()
    else:
        session_dir = Path(session_dir)
        
    if not session_dir:
        return None
    
    # Charger les données des feuilles
    leaves_data_path = session_dir / "analysis" / "leaves_data.json"
    if not leaves_data_path.exists():
        print("Données des feuilles non trouvées")
        return None
    
    with open(leaves_data_path, 'r') as f:
        leaves_data = json.load(f)
    
    # Trouver les feuilles visitées (avec images)
    images_dir = session_dir / "images"
    visited_leaves = []
    
    if images_dir.exists():
        for img_file in images_dir.glob("leaf_*.jpg"):
            # Extraire l'ID de la feuille du nom du fichier
            filename = img_file.stem
            # Format: leaf_{id}_{timestamp}
            parts = filename.split('_')
            if len(parts) >= 2:
                try:
                    leaf_id = int(parts[1])
                    visited_leaves.append(leaf_id)
                except ValueError:
                    continue
    
    visited_leaves = list(set(visited_leaves))  # Supprimer doublons
    print(f"Feuilles visitées: {visited_leaves}")
    
    return {
        "session_dir": session_dir,
        "leaves_data": leaves_data,
        "visited_leaves": visited_leaves
    }

def load_fluorescence_data_for_leaf(session_dir, leaf_id):
    """Charge les données de fluorescence pour une feuille spécifique"""
    analysis_dir = Path(session_dir) / "analysis"
    
    # Chercher le fichier de fluorescence pour cette feuille
    fluo_files = list(analysis_dir.glob(f"fluorescence_leaf_{leaf_id}_*.json"))
    
    if not fluo_files:
        print(f"Pas de données fluorescence pour feuille {leaf_id}")
        return [], {}, {}
    
    # Prendre le fichier le plus récent
    fluo_file = sorted(fluo_files)[-1]
    
    try:
        with open(fluo_file, 'r') as f:
            fluo_data = json.load(f)
        
        measurements = fluo_data.get('measurements', [])
        
        # Créer timeline basée sur la fréquence (simulée)
        freq = 20.0  # Hz par défaut
        time_points = [i/freq for i in range(len(measurements))]
        
        config = {
            'frequency': freq,
            'name': f'Leaf {leaf_id} Fluorescence'
        }
        
        print(f"Données fluorescence chargées pour feuille {leaf_id}: {len(measurements)} points")
        return time_points, measurements, config
        
    except Exception as e:
        print(f"Erreur chargement fluorescence feuille {leaf_id}: {e}")
        return [], {}, {}

def load_pointcloud_with_targeting(session_dir, leaves_data, visited_leaves,
                                   max_bg_points=3000):
    """
    Charge le point cloud brut downsamplé (fond uniquement).
    Les feuilles visitées sont rendues via des traces séparées dans build_visits_figure.
    """
    pointcloud_path = Path(session_dir) / "pointcloud.ply" if session_dir else None

    try:
        import open3d as o3d
        pcd = o3d.io.read_point_cloud(str(pointcloud_path))
        pts = np.asarray(pcd.points) * 0.001  # mm → m

        n = len(pts)
        if n > max_bg_points:
            idx = np.random.choice(n, max_bg_points, replace=False)
            pts = pts[idx]

        print(f"Point cloud fond: {len(pts)} pts (après downsampling)")
        return pts[:, 0], pts[:, 1], pts[:, 2]

    except Exception as e:
        print(f"Erreur lecture PLY: {e} — fallback mock")
        n = 2000
        t = np.linspace(0, 4*np.pi, n)
        x = np.cos(t) * (1 + 0.3*np.cos(3*t)) + np.random.normal(0, 0.05, n)
        y = np.sin(t) * (1 + 0.3*np.cos(3*t)) + np.random.normal(0, 0.05, n)
        z = 0.1 * np.sin(2*t) + np.random.normal(0, 0.02, n)
        return x, y, z


def build_visits_figure(pc_x, pc_y, pc_z, leaves_data, visited_leaves):
    """
    Mode 'Feuilles visitées' : fond noir + centroïdes gradient Fv/Fm noir→jaune.
    Les feuilles sans mesure apparaissent en gris.
    """
    normalized = normalize_fvfm(leaves_data, visited_leaves)

    traces = [go.Scatter3d(
        x=pc_x, y=pc_y, z=pc_z,
        mode='markers',
        marker=dict(size=1, color='black', opacity=0.4),
        name='Point cloud',
        hoverinfo='skip',
        showlegend=False,
    )]

    for leaf in leaves_data.get('leaves', []):
        if leaf['id'] not in visited_leaves:
            continue
        c    = leaf['centroid']
        lid  = leaf['id']
        fvfm = leaf.get('fvfm')

        if lid in normalized:
            col   = fvfm_to_color(normalized[lid])
            label = f'Fv/Fm={fvfm:.3f}' if fvfm is not None else 'Fv/Fm=N/A'
        else:
            col   = '#808080'
            label = 'Fv/Fm=N/A'

        traces.append(go.Scatter3d(
            x=[c[0]], y=[c[1]], z=[c[2]],
            mode='markers',
            marker=dict(size=12, color=col, symbol='circle',
                        line=dict(color='white', width=1)),
            name=f'Feuille {lid}',
            hovertemplate=f'<b>Feuille N°{lid}</b><br>{label}<extra></extra>',
        ))

    fig = go.Figure(data=traces)
    fig.update_layout(
        scene=dict(aspectmode='data'),
        margin=dict(l=0, r=0, b=0, t=30),
        title="Feuilles visitées — Gradient Fv/Fm (noir→jaune)",
    )
    return fig

def get_leaf_info_for_display(leaves_data, visited_leaves):
    """Récupère les infos de la première feuille visitée pour l'affichage"""
    if not visited_leaves:
        return {
            "leaf_id": "Aucune",
            "centroid": [0, 0, 0],
            "fvfm": None,
            "analysis_date": "N/A"
        }
    
    # Prendre la première feuille visitée
    first_leaf_id = visited_leaves[0]
    
    for leaf in leaves_data.get('leaves', []):
        if leaf['id'] == first_leaf_id:
            return {
                "leaf_id": f"LEAF_{leaf['id']:03d}",
                "centroid": leaf['centroid'],
                "fvfm": leaf.get('fvfm'),
                "analysis_date": "2025-12-11"
            }
    
    return {
        "leaf_id": f"LEAF_{first_leaf_id:03d}",
        "centroid": [0, 0, 0],
        "fvfm": None,
            
        "analysis_date": "2025-12-11"
    }

def load_leaf_image_for_display(session_dir, visited_leaves):
    """Charge l'image de la première feuille visitée"""
    if not visited_leaves:
        return None
    
    images_dir = Path(session_dir) / "images"
    first_leaf_id = visited_leaves[0]
    
    # Chercher l'image de cette feuille
    img_files = list(images_dir.glob(f"leaf_{first_leaf_id}_*.jpg"))
    
    if not img_files:
        return None
    
    # Prendre la première image trouvée
    img_path = img_files[0]
    
    try:
        with open(img_path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode()
        return f"data:image/jpeg;base64,{encoded}"
    except Exception as e:
        print(f"Erreur chargement image: {e}")
        return None

def load_segmentation_data(session_dir, max_pts_per_leaf=500):
    """
    Charge segmentation.ply + segmentation_labels.npy.
    Downsample à max_pts_per_leaf points par feuille pour fluidité.
    """
    seg_ply    = Path(session_dir) / "segmentation.ply"
    seg_labels = Path(session_dir) / "segmentation_labels.npy"

    if not seg_ply.exists() or not seg_labels.exists():
        print("Fichiers de segmentation absents — mode segmentation indisponible")
        return None

    try:
        import open3d as o3d
        pcd    = o3d.io.read_point_cloud(str(seg_ply))
        pts    = np.asarray(pcd.points)   # déjà en mètres (sauvegardé en m)
        labels = np.load(seg_labels)

        # Downsampling par feuille
        unique_ids = np.unique(labels)
        xs, ys, zs, ls = [], [], [], []
        for lid in unique_ids:
            mask = labels == lid
            ix = np.where(mask)[0]
            if len(ix) > max_pts_per_leaf:
                ix = np.random.choice(ix, max_pts_per_leaf, replace=False)
            xs.append(pts[ix, 0]); ys.append(pts[ix, 1])
            zs.append(pts[ix, 2]); ls.append(np.full(len(ix), lid, dtype=np.uint16))

        x_out = np.concatenate(xs)
        y_out = np.concatenate(ys)
        z_out = np.concatenate(zs)
        l_out = np.concatenate(ls)

        print(f"Segmentation chargée: {len(x_out)} pts affichés, "
              f"{len(unique_ids)} feuilles (max {max_pts_per_leaf} pts/feuille)")
        return {"x": x_out, "y": y_out, "z": z_out, "labels": l_out}

    except Exception as e:
        print(f"Erreur chargement segmentation: {e}")
        return None


def build_segmentation_figure(session_dir, leaves_data, pc_x, pc_y, pc_z):
    """
    Mode Segmentation — reproduit fidèlement interactive_selector.py :
    - Fond du nuage en noir, alpha 0.4, size 1
    - Une trace par feuille (points colorés, size 3)
    - Centroïde plus gros (size 10) avec contour noir
    - Hover "Feuille N°X"
    """
    import colorsys

    def _hsv_colors(n):
        """Même algo que generate_distinct_colors() dans interactive_selector."""
        hexcols = []
        for i in range(n):
            h = i / n
            s = 0.7 + 0.3 * (i % 2)
            v = 0.8 + 0.2 * (i % 3)
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            ri=min(255,max(0,int(r*255))); gi=min(255,max(0,int(g*255))); bi=min(255,max(0,int(b*255))); hexcols.append(f'#{ri:02x}{gi:02x}{bi:02x}')
        return hexcols

    seg = load_segmentation_data(session_dir)
    all_leaves = leaves_data.get('leaves', [])
    n_leaves   = len(all_leaves)
    colors     = _hsv_colors(n_leaves)

    # Map leaf id → index pour la couleur
    id_to_idx = {leaf['id']: i for i, leaf in enumerate(all_leaves)}

    traces = []

    # ── Fond nuage ──────────────────────────────────────────────────────────
    traces.append(go.Scatter3d(
        x=pc_x, y=pc_y, z=pc_z,
        mode='markers',
        marker=dict(size=1, color='black', opacity=0.4),
        name='Point cloud',
        hoverinfo='skip',
        showlegend=False,
    ))

    if seg is not None:
        x, y, z, labels = seg['x'], seg['y'], seg['z'], seg['labels']

        for i, leaf in enumerate(all_leaves):
            lid  = leaf['id']
            col  = colors[id_to_idx.get(lid, 0)]
            mask = labels == lid
            if not mask.any():
                continue

            # ── Points de la feuille ────────────────────────────────────
            traces.append(go.Scatter3d(
                x=x[mask], y=y[mask], z=z[mask],
                mode='markers',
                marker=dict(size=2, color=col, opacity=0.60),
                name=f'Feuille {lid}',
                legendgroup=f'leaf_{lid}',
                hovertemplate=f'<b>Feuille N°{lid}</b><extra></extra>',
                showlegend=True,
            ))

            # ── Centroïde + numéro ──────────────────────────────────────
            c = leaf['centroid']
            traces.append(go.Scatter3d(
                x=[c[0]], y=[c[1]], z=[c[2]],
                mode='markers+text',
                marker=dict(size=8, color=col, line=dict(color='black', width=2)),
                text=[str(lid)],
                textposition='top center',
                textfont=dict(size=11, color='black'),
                name=f'Feuille {lid}',
                legendgroup=f'leaf_{lid}',
                showlegend=False,
                hovertemplate=f'<b>Feuille N°{lid}</b><br>'
                              f'({c[0]:.3f}, {c[1]:.3f}, {c[2]:.3f})<extra></extra>',
            ))

            # ── Normale (vraie flèche : ligne + cône à la pointe) ──────
            if 'normal' in leaf:
                n   = leaf['normal']
                nl  = 0.05          # longueur du fût 5 cm
                tip = [c[0] + n[0]*nl, c[1] + n[1]*nl, c[2] + n[2]*nl]

                # Fût de la flèche
                traces.append(go.Scatter3d(
                    x=[c[0], tip[0]], y=[c[1], tip[1]], z=[c[2], tip[2]],
                    mode='lines',
                    line=dict(color='red', width=4),
                    showlegend=False,
                    hoverinfo='skip',
                ))

                # Tête de la flèche
                head = 0.012  # taille du cône
                traces.append(go.Cone(
                    x=[tip[0]], y=[tip[1]], z=[tip[2]],
                    u=[n[0]*head], v=[n[1]*head], w=[n[2]*head],
                    colorscale=[[0, 'red'], [1, 'red']],
                    showscale=False,
                    sizemode='absolute',
                    sizeref=head,
                    anchor='tail',
                    showlegend=False,
                    hoverinfo='skip',
                ))

    else:
        # Pas de segmentation : centroïdes uniquement
        for i, leaf in enumerate(all_leaves):
            lid = leaf['id']
            col = colors[id_to_idx.get(lid, 0)]
            c   = leaf['centroid']
            traces.append(go.Scatter3d(
                x=[c[0]], y=[c[1]], z=[c[2]],
                mode='markers+text',
                marker=dict(size=12, color=col, symbol='diamond',
                            line=dict(color='black', width=2)),
                text=[str(lid)],
                textposition='top center',
                textfont=dict(size=12, color='black'),
                name=f'Feuille {lid}',
                hovertemplate=f'<b>Feuille N°{lid}</b><extra></extra>',
            ))

    fig = go.Figure(data=traces)
    fig.update_layout(
        scene=dict(aspectmode='data'),
        margin=dict(l=0, r=0, b=0, t=30),
        title=f"Segmentation — {n_leaves} feuilles détectées",
        legend=dict(itemsizing='constant', font=dict(size=10),
                    title=dict(text='Feuilles')),
    )
    return fig

# Chargement initial des données
targeting_data = load_targeting_data()

if targeting_data:
    session_dir = targeting_data["session_dir"]
    leaves_data = targeting_data["leaves_data"] 
    visited_leaves = targeting_data["visited_leaves"]
    
    # Ne pas pré-charger les données de feuille - attendre sélection utilisateur
    current_leaf_id = None
    pc_x, pc_y, pc_z = load_pointcloud_with_targeting(session_dir, leaves_data, visited_leaves)
    
    # États par défaut "Aucune données chargées"
    time_data, fluor_data, fluor_config = [], [], {}
    leaf_info = {
        "leaf_id": "⌀",
        "centroid": "Aucune feuille sélectionnée",
        "fvfm": None,
        "analysis_date": "N/A"
    }
    leaf_image_src = None
    
    print(f"Données chargées pour {len(visited_leaves)} feuilles visitées - En attente de sélection utilisateur")
else:
    # Fallback données mock
    print("Aucune donnée de targeting, utilisation données mock")
    time_data, fluor_data, fluor_config = [0, 1, 2, 3, 4], [0.016, 0.008, 0.014, 0.009, 0.014], {}

    n_points = 1000
    pc_x = np.random.normal(0.2, 0.1, n_points)
    pc_y = np.random.normal(0.2, 0.1, n_points)
    pc_z = np.random.uniform(0.0, 0.4, n_points)

    leaf_info = {
        "leaf_id": "MOCK_001",
        "centroid": [0.2, 0.2, 0.2],
        "fvfm": None,
        "analysis_date": "2025-12-11"
    }
    leaf_image_src = None
    visited_leaves = []
    session_dir = None
    leaves_data = {"leaves": []}

# Layout responsive
app.layout = html.Div([
    html.H1("Leaf Targeting Results Viewer - ROMI", 
            style={
                'textAlign': 'center', 
                'marginBottom': '20px', 
                'color': '#2d5016',
                'fontFamily': 'Georgia, serif',  # Police serif élégante
                'fontWeight': 'bold',
                'fontSize': '28px',
                'textShadow': '1px 1px 2px rgba(0,0,0,0.1)'
            }),
    
    # Sélection de session
    html.Div([
        html.H3("Session Selection", style={'margin': '0 0 10px 0', 'fontSize': '16px'}),
        html.Div([
            html.Label("Choisir une session:", style={'fontSize': '12px', 'marginBottom': '5px'}),
            html.Div([
                dcc.Dropdown(
                    id='session-selector',
                    options=find_all_targeting_sessions(),
                    value=find_all_targeting_sessions()[0]['value'] if find_all_targeting_sessions() and find_all_targeting_sessions()[0]['value'] else None,
                    placeholder="Sélectionner une session...",
                    style={'fontSize': '12px', 'flex': '1'}
                ),
                html.Button("Actualiser", id='refresh-sessions-btn', n_clicks=0,
                    title="Actualiser la liste des sessions",
                    style={
                        'fontSize': '12px',
                        'padding': '0 14px',
                        'cursor': 'pointer',
                        'border': '1px solid #2d5016',
                        'borderRadius': '4px',
                        'backgroundColor': '#2d5016',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'marginLeft': '8px',
                        'whiteSpace': 'nowrap',
                        'height': '36px',
                    }),
            ], style={'display': 'flex', 'alignItems': 'center'}),
        ]),
        html.Div(id='current-session-info',
                children=f"Session actuelle : {targeting_data['session_dir'].name if targeting_data else 'Aucune'}",
                style={'fontSize': '11px', 'color': '#666', 'marginTop': '6px'})
    ], style={
        'border': '1px solid #000',
        'borderRadius': '5px',
        'backgroundColor': 'white',
        'padding': '10px',
        'marginBottom': '10px'
    }),
    
    # Signal invisible pour déclencher la mise à jour des callbacks
    html.Div(id='session-changed-signal', style={'display': 'none'}, children='0'),

    html.Div([
        # Zone principale - Point Cloud (plus étroite)
        html.Div([
            # Toggle vue
            html.Div([
                dcc.RadioItems(
                    id='view-mode',
                    options=[
                        {'label': 'Segmentation', 'value': 'segmentation'},
                        {'label': 'Mesures', 'value': 'visits'},
                    ],
                    value='segmentation',
                    inline=True,
                    style={'fontSize': '12px', 'padding': '6px 10px'}
                ),
            ], style={
                'borderBottom': '1px solid #ddd',
                'backgroundColor': '#f8f9fa',
            }),
            dcc.Graph(
                id='pointcloud-3d',
                figure=build_visits_figure(pc_x, pc_y, pc_z, leaves_data, visited_leaves),
                style={'height': '500px', 'width': '100%'}
            )
        ], style={
            'width': 'calc(100% - 610px)',  # Largeur dynamique: 100% - maxWidth colonne droite (600px) - marginRight (10px)
            'marginRight': '10px',
            'minWidth': '300px',
            'border': '1px solid #000',  # Bordure noire fine
            'borderRadius': '5px',
            'backgroundColor': 'white'
        }),
        
        # Panneau de droite (plus large)
        html.Div([
            # Info panel - maintenant dynamique
            html.Div([
                html.H4("Informations Feuille", style={'marginBottom': '10px', 'fontSize': '14px'}),
                html.Div([
                    html.Div("⌀ Aucune feuille sélectionnée", 
                            style={'textAlign': 'center', 'color': '#666', 'fontSize': '12px', 
                                   'padding': '20px', 'fontStyle': 'italic'})
                ], id='leaf-info-content')
            ], style={
                'backgroundColor': '#f8f9fa', 
                'padding': '15px', 
                'borderRadius': '5px',
                'marginBottom': '10px',
                'height': '180px',
                'overflow': 'auto',
                'border': '1px solid #000'  # Bordure noire fine
            }),
            
            # Image panel avec ratio 16:9 - maintenant dynamique
            html.Div([
                html.H4("Image Feuille", style={'marginBottom': '10px', 'fontSize': '14px'}),
                html.Div([
                    html.Div(
                        "⌀ Aucune image chargée",
                        style={
                            'height': '160px', 'backgroundColor': '#f5f5f5', 'display': 'flex',
                            'alignItems': 'center', 'justifyContent': 'center',
                            'borderRadius': '5px', 'fontSize': '12px', 'color': '#666',
                            'border': '2px dashed #ccc', 'fontStyle': 'italic'
                        }
                    )
                ], id='leaf-image-content')
            ], style={
                'flex': '1',
                'border': '1px solid #000',  # Bordure noire fine
                'borderRadius': '5px',
                'backgroundColor': 'white',
                'padding': '10px'
            })
        ], style={
            'width': '63%',  # Beaucoup plus grand (était 48%)
            'display': 'flex', 
            'flexDirection': 'column',
            'minWidth': '280px',
            'maxWidth': '600px'   # Augmenté aussi
        })
    ], style={
        'display': 'flex', 
        'justifyContent': 'space-between',  # Aligner correctement les blocs
        'height': 'auto',
        'minHeight': '500px',
        'marginBottom': '30px',
        'gap': '0px'  # Supprimer gap qui décale
    }),
    
    # Graphique fluorescence en bas - maintenant dynamique
    html.Div([
        dcc.Graph(
            id='fluorescence-chart',
            figure=go.Figure().update_layout(
                title="⌀ Aucune données de fluorescence chargées",
                xaxis_title="Temps (s)",
                yaxis_title="Intensité", 
                margin=dict(l=50, r=50, b=50, t=50),
                showlegend=False,
                plot_bgcolor='white',
                height=280,
                annotations=[{
                    'text': 'Cliquez sur une feuille dans le point cloud<br>pour afficher ses données de fluorescence',
                    'xref': 'paper', 'yref': 'paper',
                    'x': 0.5, 'y': 0.5, 'xanchor': 'center', 'yanchor': 'middle',
                    'showarrow': False, 'font': {'size': 14, 'color': '#666'}
                }]
            )
        )
    ], style={
        'border': '1px solid #000',  # Bordure noire fine
        'borderRadius': '5px',
        'backgroundColor': 'white',
        'padding': '10px',  # Plus de padding interne
        'marginTop': '10px'  # Marge en haut pour séparer des blocs du dessus
    }),
    
    html.Hr(),
    html.P("Sony Computer Science Laboratories - 2025/2026", 
           style={'textAlign': 'center', 'color': '#666'})
], style={
    'padding': '20px', 
    'fontFamily': 'Arial', 
    'maxWidth': '100%', 
    'overflow': 'hidden',
    'backgroundColor': '#f5f7fa',  # Fond gris-bleu clair
    'minHeight': '100vh'  # Hauteur min plein écran
})

# Ajout de CSS pour responsive design
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            @media (max-width: 768px) {
                .main-container {
                    flex-direction: column !important;
                    height: auto !important;
                }
                .main-container > div {
                    min-width: 100% !important;
                    margin-right: 0 !important;
                    margin-bottom: 10px !important;
                }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Variables globales pour callbacks
app_data = {
    'targeting_data': targeting_data,
    'session_dir': session_dir,
    'leaves_data': leaves_data,
    'visited_leaves': visited_leaves,
    'current_leaf_id': current_leaf_id if targeting_data else None  # None au lieu de 1
}

def find_clicked_leaf(click_data, visited_leaves, leaves_data):
    """Trouve la feuille la plus proche du point cliqué"""
    if not click_data or not click_data.get('points'):
        return None
    
    # Coordonnées du clic
    clicked_point = click_data['points'][0]
    click_x = clicked_point['x']
    click_y = clicked_point['y'] 
    click_z = clicked_point['z']
    
    # Trouver la feuille la plus proche
    min_distance = float('inf')
    closest_leaf_id = None
    
    for leaf in leaves_data.get('leaves', []):
        if leaf['id'] in visited_leaves:
            centroid = leaf['centroid']
            
            # Distance euclidienne
            distance = ((click_x - centroid[0])**2 + 
                       (click_y - centroid[1])**2 + 
                       (click_z - centroid[2])**2)**0.5
            
            if distance < min_distance:
                min_distance = distance
                closest_leaf_id = leaf['id']
    
    # Seuil de proximité (2cm)
    if min_distance < 0.02:
        return closest_leaf_id
    return None

def get_leaf_info_by_id(leaf_id, leaves_data):
    """Récupère les infos d'une feuille par son ID"""
    for leaf in leaves_data.get('leaves', []):
        if leaf['id'] == leaf_id:
            return {
                "leaf_id": f"LEAF_{leaf['id']:03d}",
                "centroid": leaf['centroid'],
                "fvfm": leaf.get('fvfm'),
                "analysis_date": "2025-12-11"
            }
    return {
        "leaf_id": f"LEAF_{leaf_id:03d}",
        "centroid": [0, 0, 0],
        "fvfm": None,
            
        "analysis_date": "2025-12-11"
    }

def get_leaf_image_by_id(leaf_id, session_dir):
    """Charge l'image d'une feuille par son ID"""
    if not session_dir:
        return None
    
    images_dir = Path(session_dir) / "images"
    img_files = list(images_dir.glob(f"leaf_{leaf_id}_*.jpg"))
    
    if not img_files:
        return None
    
    img_path = img_files[0]
    
    try:
        with open(img_path, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode()
        return f"data:image/jpeg;base64,{encoded}"
    except Exception as e:
        print(f"Erreur chargement image feuille {leaf_id}: {e}")
        return None

# Callback pour actualiser la liste des sessions
@app.callback(
    [Output('session-selector', 'options'),
     Output('session-selector', 'value')],
    [Input('refresh-sessions-btn', 'n_clicks')],
    [State('session-selector', 'value')],
    prevent_initial_call=True
)
def refresh_sessions(n_clicks, current_value):
    sessions = find_all_targeting_sessions()
    # Conserver la session courante si elle existe encore, sinon prendre la plus récente
    existing_values = [s['value'] for s in sessions]
    new_value = current_value if current_value in existing_values else (sessions[0]['value'] if sessions else None)
    print(f"Sessions actualisées: {len(sessions)} session(s) trouvée(s)")
    return sessions, new_value


# Callback pour charger une session sélectionnée (dropdown direct)
@app.callback(
    [Output('current-session-info', 'children'),
     Output('session-changed-signal', 'children')],
    [Input('session-selector', 'value')]
)
def load_selected_session(selected_session_path):
    if not selected_session_path:
        raise PreventUpdate

    # Charger les nouvelles données de session
    new_targeting_data = load_targeting_data(selected_session_path)

    if not new_targeting_data:
        raise PreventUpdate

    # Mettre à jour app_data globales
    app_data['targeting_data'] = new_targeting_data
    app_data['session_dir'] = new_targeting_data['session_dir']
    app_data['leaves_data'] = new_targeting_data['leaves_data']
    app_data['visited_leaves'] = new_targeting_data['visited_leaves']
    app_data['current_leaf_id'] = None

    session_name = Path(selected_session_path).name
    session_info_text = f"Session actuelle : {session_name}"

    import time as _time
    signal_value = str(int(_time.time()))

    return session_info_text, signal_value


# Callback pointcloud — se déclenche sur changement de session ou de mode
@app.callback(
    Output('pointcloud-3d', 'figure'),
    [Input('session-changed-signal', 'children'),
     Input('view-mode', 'value')]
)
def update_pointcloud_figure(session_signal, view_mode):
    """
    Reconstruit la figure 3D uniquement quand la session ou le mode change.
    En mode visits, relit le dossier images/ pour être à jour.
    """
    session_dir  = app_data.get('session_dir')
    leaves_data  = app_data.get('leaves_data', {"leaves": []})

    # Rafraîchir visited_leaves depuis le disque à chaque changement de mode/session
    if session_dir:
        images_dir = Path(session_dir) / "images"
        visited = []
        if images_dir.exists():
            for img_file in images_dir.glob("leaf_*.jpg"):
                parts = img_file.stem.split('_')
                if len(parts) >= 2:
                    try:
                        visited.append(int(parts[1]))
                    except ValueError:
                        pass
        app_data['visited_leaves'] = list(set(visited))

    visited_leaves = app_data.get('visited_leaves', [])

    pc_x, pc_y, pc_z = load_pointcloud_with_targeting(
        session_dir, leaves_data, visited_leaves
    )

    if view_mode == 'segmentation' and session_dir:
        return build_segmentation_figure(session_dir, leaves_data, pc_x, pc_y, pc_z)

    return build_visits_figure(pc_x, pc_y, pc_z, leaves_data, visited_leaves)


# Callback pour mise à jour des infos feuille
@app.callback(
    Output('leaf-info-content', 'children'),
    [Input('pointcloud-3d', 'clickData'),
     Input('session-changed-signal', 'children')],
    prevent_initial_call=True
)
def update_leaf_info(click_data, session_signal):
    # Chercher si une feuille a été cliquée
    clicked_leaf_id = find_clicked_leaf(click_data, app_data['visited_leaves'], app_data['leaves_data'])
    
    if clicked_leaf_id and clicked_leaf_id != app_data['current_leaf_id']:
        app_data['current_leaf_id'] = clicked_leaf_id
        print(f"Feuille sélectionnée: {clicked_leaf_id}")
    
    # Si aucune feuille sélectionnée, afficher état par défaut
    if app_data['current_leaf_id'] is None:
        return [
            html.Div("⌀ Aucune feuille sélectionnée", 
                    style={'textAlign': 'center', 'color': '#666', 'fontSize': '12px', 
                           'padding': '20px', 'fontStyle': 'italic'})
        ]
    
    # Sinon, afficher les infos de la feuille
    leaf_info = get_leaf_info_by_id(app_data['current_leaf_id'], app_data['leaves_data'])
    
    return [
        html.P(f"ID: {leaf_info['leaf_id']}", style={'margin': '5px 0', 'fontSize': '12px'}),
        html.P(f"Centroïde: {leaf_info['centroid']}", style={'margin': '5px 0', 'fontSize': '12px'}),
        html.P(f"Fv/Fm: {leaf_info['fvfm']:.4f}" if leaf_info.get('fvfm') is not None else "Fv/Fm: N/A", style={'margin': '5px 0', 'fontSize': '12px'}),
        html.P(f"Date: {leaf_info['analysis_date']}", style={'margin': '5px 0', 'fontSize': '12px'})
    ]

# Callback pour mise à jour de l'image
@app.callback(
    Output('leaf-image-content', 'children'),
    [Input('pointcloud-3d', 'clickData'),
     Input('session-changed-signal', 'children')],
    prevent_initial_call=True
)
def update_leaf_image(click_data, session_signal):
    # Chercher si une feuille a été cliquée
    clicked_leaf_id = find_clicked_leaf(click_data, app_data['visited_leaves'], app_data['leaves_data'])
    
    if clicked_leaf_id:
        app_data['current_leaf_id'] = clicked_leaf_id
    
    # Si aucune feuille sélectionnée, afficher état par défaut
    if app_data['current_leaf_id'] is None:
        return html.Div(
            "⌀ Aucune image chargée",
            style={
                'height': '160px', 'backgroundColor': '#f5f5f5', 'display': 'flex',
                'alignItems': 'center', 'justifyContent': 'center',
                'borderRadius': '5px', 'fontSize': '12px', 'color': '#666',
                'border': '2px dashed #ccc', 'fontStyle': 'italic'
            }
        )
    
    # Sinon, charger l'image de la feuille
    leaf_image_src = get_leaf_image_by_id(app_data['current_leaf_id'], app_data['session_dir'])
    
    if leaf_image_src:
        return html.Img(
            src=leaf_image_src,
            style={
                'width': '100%',
                'height': 'auto',
                'maxHeight': '160px',
                'aspectRatio': '16/9',
                'objectFit': 'contain',
                'borderRadius': '5px',
                'backgroundColor': '#e9ecef'
            }
        )
    else:
        return html.Div(
            f"Image feuille {app_data['current_leaf_id']} non trouvée",
            style={
                'height': '160px',
                'backgroundColor': '#e9ecef',
                'display': 'flex',
                'alignItems': 'center',
                'justifyContent': 'center',
                'borderRadius': '5px',
                'color': '#6c757d',
                'fontSize': '12px',
                'aspectRatio': '16/9'
            }
        )


# Callback pour mise à jour du graphique
@app.callback(
    Output('fluorescence-chart', 'figure'),
    [Input('pointcloud-3d', 'clickData'),
     Input('session-changed-signal', 'children')],
    prevent_initial_call=True
)
def update_fluorescence_chart(click_data, session_signal):
    # Chercher si une feuille a été cliquée
    clicked_leaf_id = find_clicked_leaf(click_data, app_data['visited_leaves'], app_data['leaves_data'])
    
    if clicked_leaf_id:
        app_data['current_leaf_id'] = clicked_leaf_id
    
    leaf_id = app_data['current_leaf_id']
    
    # Si aucune feuille sélectionnée, afficher état par défaut
    if leaf_id is None:
        return go.Figure().update_layout(
            title="⌀ Aucune données de fluorescence chargées",
            xaxis_title="Temps (s)",
            yaxis_title="Intensité", 
            margin=dict(l=50, r=50, b=50, t=50),
            showlegend=False,
            annotations=[{
                'text': 'Cliquez sur une feuille dans le point cloud<br>pour afficher ses données de fluorescence',
                'xref': 'paper', 'yref': 'paper',
                'x': 0.5, 'y': 0.5, 'xanchor': 'center', 'yanchor': 'middle',
                'showarrow': False, 'font': {'size': 14, 'color': '#666'}
            }]
        )
    
    # Sinon, charger données fluorescence pour cette feuille
    if app_data['session_dir']:
        time_data, fluor_data, fluor_config = load_fluorescence_data_for_leaf(app_data['session_dir'], leaf_id)
    else:
        time_data, fluor_data, fluor_config = [0, 1, 2, 3, 4], [0.016, 0.008, 0.014, 0.009, 0.014], {}
    
    return go.Figure(data=[go.Scatter(
        x=time_data, 
        y=fluor_data,
        mode='lines+markers',
        name='Fluorescence',
        line=dict(color='green', width=3)
    )]).update_layout(
        title=f"Mesure Fluorescence - Feuille {leaf_id}",
        xaxis_title="Temps (s)",
        yaxis_title="Intensité",
        margin=dict(l=50, r=50, b=50, t=50),
        plot_bgcolor='white',
        height=280
    )

def main():
    """Lance l'application en mode navigateur"""
    print("Démarrage du Leaf Targeting Results Viewer...")
    print("=" * 50)
    
    # Déterminer l'IP de la machine
    import socket
    try:
        # Obtenir l'IP locale
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "localhost"
    
    print(f"URL: http://{local_ip}:8050")
    print("Arrêt: Ctrl+C")
    if targeting_data:
        print(f"Session: {targeting_data['session_dir'].name}")
        print(f"Feuilles visitées: {len(targeting_data['visited_leaves'])}")
    else:
        print(" Mode fallback: données mock")
    print("=" * 50)
    
    # Lancer l'application (accessible depuis le réseau)
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)  # Supprimer warning
    app.run(debug=False, port=8050, host='0.0.0.0')

if __name__ == '__main__':
    main()