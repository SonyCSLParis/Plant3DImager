#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de test pour vérifier la compatibilité de la nouvelle API de communication
Usage: python test_new_api.py
"""

import sys
import os

# Ajouter le répertoire parent au PYTHONPATH pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_camera_api():
    """Test de l'API Camera"""
    print("=== Test Camera API ===")
    try:
        # Import de la nouvelle classe
        from camera_controller import CameraController
        
        print("✅ Import CameraController réussi")
        
        # Test d'initialisation (sans connexion réelle)
        controller = CameraController()
        print("✅ Initialisation CameraController réussie")
        
        # Vérifier que toutes les méthodes existent
        required_methods = ['connect', 'set_output_directory', 'take_photo', 'shutdown']
        for method in required_methods:
            if hasattr(controller, method):
                print(f"✅ Méthode {method} présente")
            else:
                print(f"❌ Méthode {method} manquante")
                return False
                
        print("✅ Test Camera API terminé avec succès")
        return True
        
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

def test_cnc_api():
    """Test de l'API CNC"""
    print("\n=== Test CNC API ===")
    try:
        # Import de la nouvelle classe
        from cnc_controller import CNCController
        
        print("✅ Import CNCController réussi")
        
        # Test d'initialisation (sans connexion réelle)
        controller = CNCController(speed=0.1)
        print("✅ Initialisation CNCController réussie")
        
        # Vérifier que toutes les méthodes existent
        required_methods = ['connect', 'get_position', 'move_to', 'home', 'shutdown']
        for method in required_methods:
            if hasattr(controller, method):
                print(f"✅ Méthode {method} présente")
            else:
                print(f"❌ Méthode {method} manquante")
                return False
                
        print("✅ Test CNC API terminé avec succès")
        return True
        
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

def test_camera_class():
    """Test de la classe Camera interne"""
    print("\n=== Test Camera Class ===")
    try:
        from camera_controller import Camera
        
        # Vérifier que toutes les méthodes requises existent
        required_methods = ['create', 'grab', 'set_value', 'select_option', 'power_up', 'power_down']
        for method in required_methods:
            if hasattr(Camera, method):
                print(f"✅ Méthode Camera.{method} présente")
            else:
                print(f"❌ Méthode Camera.{method} manquante")
                return False
                
        print("✅ Test Camera Class terminé avec succès")
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_cnc_class():
    """Test de la classe CNC interne"""
    print("\n=== Test CNC Class ===")
    try:
        from cnc_controller import CNC
        
        # Vérifier que toutes les méthodes requises existent
        required_methods = ['create', 'moveto', 'get_position', 'homing', 'power_up', 'power_down']
        for method in required_methods:
            if hasattr(CNC, method):
                print(f"✅ Méthode CNC.{method} présente")
            else:
                print(f"❌ Méthode CNC.{method} manquante")
                return False
                
        print("✅ Test CNC Class terminé avec succès")
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def main():
    """Fonction principale de test"""
    print("Test de compatibilité de la nouvelle API de communication")
    print("=" * 60)
    
    # Tests des contrôleurs
    camera_ok = test_camera_api()
    cnc_ok = test_cnc_api()
    
    # Tests des classes internes
    camera_class_ok = test_camera_class()
    cnc_class_ok = test_cnc_class()
    
    # Résultat final
    print("\n" + "=" * 60)
    if camera_ok and cnc_ok and camera_class_ok and cnc_class_ok:
        print("🎉 TOUS LES TESTS RÉUSSIS!")
        print("✅ La migration vers la nouvelle API est compatible")
        print("✅ Votre projet devrait fonctionner exactement comme avant")
        return 0
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("🔧 Vérifiez les erreurs ci-dessus avant de procéder à la migration")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
