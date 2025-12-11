#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Diagnostic du module rcom pour identifier la bonne classe à utiliser
"""

def diagnose_rcom():
    """Diagnostique du module rcom"""
    print("=== Diagnostic du module rcom ===")
    
    try:
        import rcom.rcom_client
        print("✅ Module rcom.rcom_client importé avec succès")
        
        # Lister tous les attributs du module
        print("\n📋 Contenu du module rcom.rcom_client:")
        attributes = dir(rcom.rcom_client)
        
        for attr in sorted(attributes):
            if not attr.startswith('_'):  # Ignorer les attributs privés
                obj = getattr(rcom.rcom_client, attr)
                obj_type = type(obj).__name__
                print(f"  - {attr} ({obj_type})")
        
        # Chercher spécifiquement les classes de client
        print("\n🔍 Classes de client détectées:")
        client_classes = []
        
        for attr in attributes:
            if not attr.startswith('_'):
                obj = getattr(rcom.rcom_client, attr)
                if isinstance(obj, type):  # C'est une classe
                    if 'client' in attr.lower() or 'rcom' in attr.lower():
                        client_classes.append(attr)
                        print(f"  ✅ {attr}")
        
        if not client_classes:
            print("  ❌ Aucune classe de client évidente trouvée")
            print("\n📝 Toutes les classes disponibles:")
            for attr in attributes:
                if not attr.startswith('_'):
                    obj = getattr(rcom.rcom_client, attr)
                    if isinstance(obj, type):
                        print(f"    - {attr}")
        
        return client_classes
        
    except ImportError as e:
        print(f"❌ Impossible d'importer rcom.rcom_client: {e}")
        return []
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return []

def test_client_classes(client_classes):
    """Teste les classes de client trouvées"""
    print(f"\n=== Test des classes de client ===")
    
    for class_name in client_classes:
        try:
            import rcom.rcom_client
            client_class = getattr(rcom.rcom_client, class_name)
            
            print(f"\n🔬 Test de {class_name}:")
            
            # Examiner les méthodes de la classe
            methods = [method for method in dir(client_class) if not method.startswith('_')]
            print(f"  Méthodes disponibles: {', '.join(methods)}")
            
            # Vérifier si elle a les méthodes qu'on utilise
            required_methods = ['execute', 'binary']
            has_required = all(hasattr(client_class, method) for method in required_methods)
            
            if has_required:
                print(f"  ✅ {class_name} a toutes les méthodes requises")
            else:
                missing = [m for m in required_methods if not hasattr(client_class, m)]
                print(f"  ⚠️  {class_name} manque: {missing}")
            
        except Exception as e:
            print(f"  ❌ Erreur avec {class_name}: {e}")

def suggest_fix(client_classes):
    """Suggère une correction basée sur les classes trouvées"""
    print(f"\n=== Suggestions de correction ===")
    
    if not client_classes:
        print("❌ Aucune classe de client trouvée.")
        print("💡 Solutions possibles:")
        print("  1. Vérifier la version de rcom installée")
        print("  2. Mettre à jour rcom: pip install --upgrade rcom")
        print("  3. Vérifier la documentation rcom")
        return
    
    # Chercher la meilleure classe
    best_candidate = None
    
    for class_name in client_classes:
        if 'ws' in class_name.lower() and 'client' in class_name.lower():
            best_candidate = class_name
            break
        elif 'client' in class_name.lower():
            best_candidate = class_name
    
    if best_candidate:
        print(f"✅ Classe recommandée: {best_candidate}")
        print(f"\n📝 Remplacez dans vos fichiers:")
        print(f"   from rcom.rcom_client import RcomWSClient")
        print(f"   # par:")
        print(f"   from rcom.rcom_client import {best_candidate}")
        print(f"   # et remplacez RcomWSClient par {best_candidate}")
    else:
        print(f"⚠️  Plusieurs classes trouvées: {client_classes}")
        print(f"💡 Testez manuellement chacune pour voir laquelle fonctionne")

def main():
    """Fonction principale"""
    print("Diagnostic du module rcom")
    print("=" * 30)
    
    client_classes = diagnose_rcom()
    
    if client_classes:
        test_client_classes(client_classes)
        suggest_fix(client_classes)
    else:
        print("\n❌ Impossible de continuer sans classes de client")
    
    print(f"\n" + "=" * 50)
    print("💡 Utilisez ces informations pour corriger les imports")

if __name__ == "__main__":
    main()
