#!/usr/bin/env python3
import dash
from dash import html, dcc, Input, Output
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

app = dash.Dash(__name__)

# Health status colors mapping (pour affichage textuel)
HEALTH_COLORS = {
    "Critique": "#D32F2F",    # Rouge foncé
    "Stressé": "#FF7043",     # Orange-rouge  
    "Normal": "#FFA726",      # Orange
    "Bon": "#66BB6A",         # Vert clair
    "Excellent": "#2E7D32"    # Vert foncé
}

def get_health_color(health_status):
    """Retourne la couleur correspondant à l'état de santé (pour texte)"""
    return HEALTH_COLORS.get(health_status, "#808080")  # Gris par défaut

def normalize_fluorescence_values(leaves_data, visited_leaves):
    """Normalise les valeurs de fluorescence entre 0 et 1"""
    # Récupérer toutes les valeurs de fluorescence des feuilles visitées
    fluor_values = []
    for leaf in leaves_data.get('leaves', []):
        if leaf['id'] in visited_leaves and 'fluorescence_mean' in leaf:
            fluor_values.append(leaf['fluorescence_mean'])
    
    if not fluor_values:
        return {}
    
    # Calcul min/max pour normalisation
    min_fluor = min(fluor_values)
    max_fluor = max(fluor_values)
    
    # Eviter division par zéro
    if max_fluor == min_fluor:
        return {leaf['id']: 0.5 for leaf in leaves_data.get('leaves', []) if leaf['id'] in visited_leaves}
    
    # Normaliser chaque feuille
    normalized = {}
    for leaf in leaves_data.get('leaves', []):
        if leaf['id'] in visited_leaves and 'fluorescence_mean' in leaf:
            norm_value = (leaf['fluorescence_mean'] - min_fluor) / (max_fluor - min_fluor)
            normalized[leaf['id']] = norm_value
    
    return normalized

def fluorescence_to_color(normalized_value):
    """Convertit valeur normalisée (0-1) en couleur RGB avec gradient rouge->vert"""
    # Clamp entre 0 et 1
    value = max(0, min(1, normalized_value))
    
    # Gradient rouge (0) vers vert (1)
    # Rouge: (255, 0, 0) -> Vert: (0, 128, 0)
    red = int(255 * (1 - value))      # 255 à 0
    green = int(128 * value)          # 0 à 128  
    blue = 0                          # Toujours 0
    
    # Convertir en hex
    return f"#{red:02x}{green:02x}{blue:02x}"

def find_latest_targeting_session():
    """Trouve le répertoire de session de targeting le plus récent"""
    base_pattern = "results/leaf_targeting/leaf_analysis_*"
    session_dirs = glob.glob(base_pattern)
    
    if not session_dirs:
        print("❌ Aucun répertoire de targeting trouvé")
        return None
    
    # Trier par nom (timestamp) décroissant
    session_dirs.sort(reverse=True)
    latest_dir = session_dirs[0]
    print(f"📂 Répertoire de session trouvé: {latest_dir}")
    return Path(latest_dir)

def load_targeting_data():
    """Charge toutes les données d'une session de targeting"""
    session_dir = find_latest_targeting_session()
    if not session_dir:
        return None
    
    # Charger les données des feuilles
    leaves_data_path = session_dir / "analysis" / "leaves_data.json"
    if not leaves_data_path.exists():
        print("❌ Données des feuilles non trouvées")
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
    print(f"🍃 Feuilles visitées: {visited_leaves}")
    
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
        print(f"⚠️ Pas de données fluorescence pour feuille {leaf_id}")
        return [], {}
    
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
        
        print(f"📊 Données fluorescence chargées pour feuille {leaf_id}: {len(measurements)} points")
        return time_points, measurements, config
        
    except Exception as e:
        print(f"❌ Erreur chargement fluorescence feuille {leaf_id}: {e}")
        return [], {}

def load_pointcloud_with_targeting(session_dir, leaves_data, visited_leaves):
    """Charge le point cloud et identifie les feuilles visitées"""
    pointcloud_path = Path(session_dir) / "pointcloud.ply"
    
    try:
        from plyfile import PlyData
        
        # Lire le fichier PLY
        plydata = PlyData.read(pointcloud_path)
        vertex_data = plydata['vertex']
        
        # Extraire les coordonnées et appliquer le même scaling que le targeting
        x = vertex_data['x'] * 0.001  # Convertir mm -> m
        y = vertex_data['y'] * 0.001  # Convertir mm -> m
        z = vertex_data['z'] * 0.001  # Convertir mm -> m
        
        print(f"☁️ Point cloud chargé: {len(x)} points")
        
        # Créer array des couleurs (noir par défaut)
        colors = ['black'] * len(x)
        sizes = [1] * len(x)
        
        # Calculer les valeurs normalisées pour le gradient
        normalized_values = normalize_fluorescence_values(leaves_data, visited_leaves)
        
        # Identifier les feuilles visitées et les colorer avec gradient
        visited_centroids = []
        centroid_colors = []
        for leaf in leaves_data.get('leaves', []):
            if leaf['id'] in visited_leaves:
                centroid = leaf['centroid']
                
                # Utiliser gradient basé sur fluorescence normalisée
                if leaf['id'] in normalized_values:
                    norm_value = normalized_values[leaf['id']]
                    gradient_color = fluorescence_to_color(norm_value)
                else:
                    gradient_color = "#808080"  # Gris si pas de données
                
                visited_centroids.append(centroid)
                centroid_colors.append(gradient_color)
        
        # Ajouter les centroïdes comme points séparés (gradient, plus gros)
        if visited_centroids:
            centroids_array = np.array(visited_centroids)
            # Ajouter les centroïdes aux coordonnées
            x = np.concatenate([x, centroids_array[:, 0]])
            y = np.concatenate([y, centroids_array[:, 1]]) 
            z = np.concatenate([z, centroids_array[:, 2]])
            # Ajouter couleurs gradient et tailles pour les centroïdes
            colors.extend(centroid_colors)
            sizes.extend([15] * len(visited_centroids))  # Beaucoup plus gros
        
        return x, y, z, colors, sizes
        
    except ImportError:
        print("plyfile non installé, utilisation de trimesh...")
        try:
            import trimesh
            mesh = trimesh.load(pointcloud_path)
            if hasattr(mesh, 'vertices'):
                vertices = mesh.vertices * 0.001  # Convertir mm -> m
                x, y, z = vertices[:, 0], vertices[:, 1], vertices[:, 2]
                colors = ['black'] * len(x)
                sizes = [1] * len(x)
                
                # Calculer les valeurs normalisées pour le gradient
                normalized_values = normalize_fluorescence_values(leaves_data, visited_leaves)
                
                # Ajouter centroïdes visitées avec gradient de couleurs
                visited_centroids = []
                centroid_colors = []
                for leaf in leaves_data.get('leaves', []):
                    if leaf['id'] in visited_leaves:
                        centroid = leaf['centroid']
                        
                        # Utiliser gradient basé sur fluorescence normalisée
                        if leaf['id'] in normalized_values:
                            norm_value = normalized_values[leaf['id']]
                            gradient_color = fluorescence_to_color(norm_value)
                        else:
                            gradient_color = "#808080"  # Gris si pas de données
                        
                        visited_centroids.append(centroid)
                        centroid_colors.append(gradient_color)
                
                if visited_centroids:
                    centroids_array = np.array(visited_centroids)
                    x = np.concatenate([x, centroids_array[:, 0]])
                    y = np.concatenate([y, centroids_array[:, 1]]) 
                    z = np.concatenate([z, centroids_array[:, 2]])
                    colors.extend(centroid_colors)
                    sizes.extend([15] * len(visited_centroids))
                
                return x, y, z, colors, sizes
        except:
            print("Erreur trimesh, utilisation des données mock")
    except Exception as e:
        print(f"Erreur lecture PLY: {e}, utilisation des données mock")
    
    # Données mock pour le POC si rien ne fonctionne
    n_points = 2000
    t = np.linspace(0, 4*np.pi, n_points)
    
    x = np.cos(t) * (1 + 0.3*np.cos(3*t)) + np.random.normal(0, 0.05, n_points)
    y = np.sin(t) * (1 + 0.3*np.cos(3*t)) + np.random.normal(0, 0.05, n_points)
    z = 0.1 * np.sin(2*t) + np.random.normal(0, 0.02, n_points)
    
    colors = ['black'] * len(x)
    sizes = [1] * len(x)
    
    # Ajouter quelques centroïdes mock
    if visited_leaves:
        mock_centroids = [[0.2, 0.3, 0.1], [0.5, 0.1, 0.15]][:len(visited_leaves)]
        for centroid in mock_centroids:
            x = np.append(x, centroid[0])
            y = np.append(y, centroid[1])
            z = np.append(z, centroid[2])
            colors.append('red')
            sizes.append(15)
    
    print(f"☁️ Point cloud mock généré: {len(x)} points")
    return x, y, z, colors, sizes

def get_leaf_info_for_display(leaves_data, visited_leaves):
    """Récupère les infos de la première feuille visitée pour l'affichage"""
    if not visited_leaves:
        return {
            "leaf_id": "Aucune",
            "centroid": [0, 0, 0],
            "health_status": "Unknown",
            "analysis_date": "N/A"
        }
    
    # Prendre la première feuille visitée
    first_leaf_id = visited_leaves[0]
    
    for leaf in leaves_data.get('leaves', []):
        if leaf['id'] == first_leaf_id:
            return {
                "leaf_id": f"LEAF_{leaf['id']:03d}",
                "centroid": leaf['centroid'],
                "health_status": leaf.get('health_status', 'Unknown'),
                "analysis_date": "2025-12-11"  # Date du jour par défaut
            }
    
    return {
        "leaf_id": f"LEAF_{first_leaf_id:03d}",
        "centroid": [0, 0, 0],
        "health_status": "Unknown", 
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

# Chargement des données depuis le targeting
targeting_data = load_targeting_data()

if targeting_data:
    session_dir = targeting_data["session_dir"]
    leaves_data = targeting_data["leaves_data"] 
    visited_leaves = targeting_data["visited_leaves"]
    
    # Charger données pour affichage (première feuille par défaut)
    current_leaf_id = visited_leaves[0] if visited_leaves else 1
    time_data, fluor_data, fluor_config = load_fluorescence_data_for_leaf(session_dir, current_leaf_id)
    pc_x, pc_y, pc_z, pc_colors, pc_sizes = load_pointcloud_with_targeting(session_dir, leaves_data, visited_leaves)
    leaf_info = get_leaf_info_for_display(leaves_data, visited_leaves)
    leaf_image_src = load_leaf_image_for_display(session_dir, visited_leaves)
    
    print(f"✅ Données chargées pour {len(visited_leaves)} feuilles visitées")
else:
    # Fallback données mock
    print("⚠️ Aucune donnée de targeting, utilisation données mock")
    time_data, fluor_data, fluor_config = [0, 1, 2, 3, 4], [0.016, 0.008, 0.014, 0.009, 0.014], {}
    
    n_points = 1000
    pc_x = np.random.normal(0.2, 0.1, n_points)
    pc_y = np.random.normal(0.2, 0.1, n_points)
    pc_z = np.random.uniform(0.0, 0.4, n_points)
    pc_colors = ['black'] * n_points
    pc_sizes = [1] * n_points
    
    leaf_info = {
        "leaf_id": "MOCK_001",
        "centroid": [0.2, 0.2, 0.2],
        "health_status": "Healthy",
        "analysis_date": "2025-12-11"
    }
    leaf_image_src = None
    visited_leaves = []
    session_dir = None
    leaves_data = {"leaves": []}

# Layout responsive
app.layout = html.Div([
    html.H1("🌿 Leaf Targeting Results Viewer - ROMI", 
            style={
                'textAlign': 'center', 
                'marginBottom': '20px', 
                'color': '#2d5016',
                'fontFamily': 'Georgia, serif',  # Police serif élégante
                'fontWeight': 'bold',
                'fontSize': '28px',
                'textShadow': '1px 1px 2px rgba(0,0,0,0.1)'
            }),
    
    html.Div([
        # Zone principale - Point Cloud (plus étroite)
        html.Div([
            dcc.Graph(
                id='pointcloud-3d',
                figure=go.Figure(data=[go.Scatter3d(
                    x=pc_x, y=pc_y, z=pc_z,
                    mode='markers',
                    marker=dict(
                        size=pc_sizes, 
                        color=pc_colors,
                        line=dict(width=0)  # Pas de contour pour les points
                    ),
                    name='Point Cloud',
                    text=['Point cloud' if pc_colors[i] == 'black' else f'Feuille visitée' for i in range(len(pc_colors))],
                    hovertemplate='<b>%{text}</b><br>X: %{x:.3f}<br>Y: %{y:.3f}<br>Z: %{z:.3f}<br><i>Cliquez pour sélectionner</i><extra></extra>'
                )]).update_layout(
                    scene=dict(aspectmode='cube'),
                    margin=dict(l=0, r=0, b=0, t=30),
                    title="Point Cloud 3D - Gradient Rouge→Vert (santé des feuilles)"
                ),
                style={'height': '400px', 'width': '100%'}
            )
        ], style={
            'flex': '1.2',  # Réduit de 2 à 1.2 pour laisser plus de place à l'image
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
                    html.P(f"ID: {leaf_info['leaf_id']}", style={'margin': '5px 0', 'fontSize': '12px'}),
                    html.P(f"Centroïde: {leaf_info['centroid']}", style={'margin': '5px 0', 'fontSize': '12px'}),
                    html.P(f"État: {leaf_info['health_status']}", style={'margin': '5px 0', 'fontSize': '12px'}),
                    html.P(f"Date: {leaf_info['analysis_date']}", style={'margin': '5px 0', 'fontSize': '12px'})
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
                    html.Img(
                        src=leaf_image_src if leaf_image_src else "",
                        style={
                            'width': '100%',
                            'height': 'auto',
                            'maxHeight': '160px',
                            'aspectRatio': '16/9',
                            'objectFit': 'contain',
                            'borderRadius': '5px',
                            'backgroundColor': '#e9ecef'
                        }
                    ) if leaf_image_src else html.Div("Image non trouvée", style={
                        'height': '160px',
                        'backgroundColor': '#e9ecef',
                        'display': 'flex',
                        'alignItems': 'center',
                        'justifyContent': 'center',
                        'borderRadius': '5px',
                        'color': '#6c757d',
                        'fontSize': '12px',
                        'aspectRatio': '16/9'
                    })
                ], id='leaf-image-content', style={
                    'height': '160px',
                    'display': 'flex',
                    'alignItems': 'center',
                    'justifyContent': 'center'
                })
            ], style={
                'flex': '1',
                'border': '1px solid #000',  # Bordure noire fine
                'borderRadius': '5px',
                'backgroundColor': 'white',
                'padding': '10px'
            })
        ], style={
            'flex': '1.3',  # Augmenté de 1 à 1.3 pour plus d'espace pour l'image
            'display': 'flex', 
            'flexDirection': 'column',
            'minWidth': '280px',  # Augmenté de 250px
            'maxWidth': '400px'   # Augmenté de 350px
        })
    ], style={
        'display': 'flex', 
        'height': 'auto',  # Hauteur auto au lieu de fixe
        'minHeight': '400px',  # Hauteur minimum 
        'marginBottom': '30px',  # Plus d'espace avant le graphique du bas
        'flexWrap': 'wrap',
        'gap': '15px'  # Gap plus large
    }),
    
    # Graphique fluorescence en bas - maintenant dynamique
    html.Div([
        dcc.Graph(
            id='fluorescence-chart',
            figure=go.Figure(data=[go.Scatter(
                x=time_data, 
                y=fluor_data,
                mode='lines+markers',
                name='Fluorescence',
                line=dict(color='green', width=3)
            )]).update_layout(
                title=f"Mesure Fluorescence - {fluor_config.get('name', f'Feuille {current_leaf_id if targeting_data else 1}')}",
                xaxis_title="Temps (s)",
                yaxis_title="Intensité",
                margin=dict(l=50, r=50, b=50, t=50),
                plot_bgcolor='white',
                height=280
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
    'current_leaf_id': current_leaf_id if targeting_data else 1
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
                "health_status": leaf.get('health_status', 'Unknown'),
                "analysis_date": "2025-12-11"
            }
    return {
        "leaf_id": f"LEAF_{leaf_id:03d}",
        "centroid": [0, 0, 0],
        "health_status": "Unknown", 
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

# Callback pour mise à jour des infos feuille
@app.callback(
    Output('leaf-info-content', 'children'),
    [Input('pointcloud-3d', 'clickData')]
)
def update_leaf_info(click_data):
    # Chercher si une feuille a été cliquée
    clicked_leaf_id = find_clicked_leaf(click_data, app_data['visited_leaves'], app_data['leaves_data'])
    
    if clicked_leaf_id and clicked_leaf_id != app_data['current_leaf_id']:
        app_data['current_leaf_id'] = clicked_leaf_id
        print(f"🍃 Feuille sélectionnée: {clicked_leaf_id}")
    
    leaf_info = get_leaf_info_by_id(app_data['current_leaf_id'], app_data['leaves_data'])
    
    return [
        html.P(f"ID: {leaf_info['leaf_id']}", style={'margin': '5px 0', 'fontSize': '12px'}),
        html.P(f"Centroïde: {leaf_info['centroid']}", style={'margin': '5px 0', 'fontSize': '12px'}),
        html.P(f"État: {leaf_info['health_status']}", style={'margin': '5px 0', 'fontSize': '12px'}),
        html.P(f"Date: {leaf_info['analysis_date']}", style={'margin': '5px 0', 'fontSize': '12px'})
    ]

# Callback pour mise à jour de l'image
@app.callback(
    Output('leaf-image-content', 'children'),
    [Input('pointcloud-3d', 'clickData')]
)
def update_leaf_image(click_data):
    # Chercher si une feuille a été cliquée
    clicked_leaf_id = find_clicked_leaf(click_data, app_data['visited_leaves'], app_data['leaves_data'])
    
    if clicked_leaf_id:
        app_data['current_leaf_id'] = clicked_leaf_id
    
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
    [Input('pointcloud-3d', 'clickData')]
)
def update_fluorescence_chart(click_data):
    # Chercher si une feuille a été cliquée
    clicked_leaf_id = find_clicked_leaf(click_data, app_data['visited_leaves'], app_data['leaves_data'])
    
    if clicked_leaf_id:
        app_data['current_leaf_id'] = clicked_leaf_id
    
    leaf_id = app_data['current_leaf_id']
    
    # Charger données fluorescence pour cette feuille
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
    print("🚀 Démarrage du Leaf Targeting Results Viewer...")
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
    
    print(f"🌐 URL: http://{local_ip}:8050")
    print("ℹ️  Arrêt: Ctrl+C")
    if targeting_data:
        print(f"📂 Session: {targeting_data['session_dir'].name}")
        print(f"🍃 Feuilles visitées: {len(targeting_data['visited_leaves'])}")
    else:
        print("⚠️  Mode fallback: données mock")
    print("=" * 50)
    
    # Lancer l'application (accessible depuis le réseau)
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)  # Supprimer warning
    app.run(debug=False, port=8050, host='0.0.0.0')

if __name__ == '__main__':
    main()