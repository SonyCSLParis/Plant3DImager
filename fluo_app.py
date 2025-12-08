#!/usr/bin/env python3
"""
Interface complète pour le capteur de fluorescence ROMI
Application structurée avec gestion des configurations, mesures et analyses
"""

import os
import json
import csv
import time
import numpy as np
from datetime import datetime
from romi_fluo import FluoSensor

# Import matplotlib avec gestion d'erreur
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️  matplotlib non disponible - fonctionnalités graphiques désactivées")

class FluorescenceApp:
    """Application principale pour la gestion du capteur de fluorescence"""
    
    def __init__(self):
        """Initialise l'application"""
        self.sensor = None
        self.last_measurement = None
        self.last_config_used = None
        self.measurement_history = []
        
        # Dossier pour sauvegardes
        self.output_dir = "fluorescence_data"
        os.makedirs(self.output_dir, exist_ok=True)
        
        print("🔬 Interface Capteur de Fluorescence ROMI")
        print("="*50)
    
    def connect_sensor(self):
        """Connexion au capteur"""
        try:
            if self.sensor is None:
                print("🔄 Connexion au capteur...")
                self.sensor = FluoSensor("fluo", "fluo")
                print("✅ Capteur connecté avec succès\n")
            return True
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            return False
    
    def print_menu(self, title, options):
        """Affiche un menu formaté"""
        print(f"\n{'='*60}")
        print(f"📋 {title}")
        print("="*60)
        for key, value in options.items():
            print(f"{key}. {value}")
        print()
    
    def get_user_choice(self, prompt="Votre choix: ", valid_choices=None):
        """Récupère et valide la saisie utilisateur"""
        while True:
            try:
                choice = input(prompt).strip().lower()
                if valid_choices and choice not in valid_choices:
                    print(f"Choix invalide. Options: {', '.join(valid_choices)}")
                    continue
                return choice
            except KeyboardInterrupt:
                return 'q'
    
    # =========================
    # GESTION DES CONFIGURATIONS
    # =========================
    
    def manage_configurations(self):
        """Menu de gestion des configurations"""
        while True:
            options = {
                "1": "📋 Lister les configurations",
                "2": "➕ Créer une configuration",
                "3": "✏️  Modifier une configuration",
                "4": "🗑️  Supprimer une configuration",
                "5": "🎯 Changer configuration active",
                "6": "📄 Voir détails config active",
                "r": "🔙 Retour menu principal"
            }
            
            self.print_menu("GESTION DES CONFIGURATIONS", options)
            choice = self.get_user_choice("Votre choix: ", ["1", "2", "3", "4", "5", "6", "r"])
            
            if choice == "1":
                self.list_configurations()
            elif choice == "2":
                self.create_configuration()
            elif choice == "3":
                self.modify_configuration()
            elif choice == "4":
                self.delete_configuration()
            elif choice == "5":
                self.change_active_configuration()
            elif choice == "6":
                self.show_active_config_details()
            elif choice == "r":
                break
    
    def list_configurations(self):
        """Liste toutes les configurations disponibles"""
        print("\n📋 Liste des configurations:")
        try:
            configs = self.sensor.list_configs()
            active = self.sensor.get_active_config()
            
            for i, config in enumerate(configs, 1):
                marker = "🎯" if config == active else "  "
                print(f"{marker} {i}. {config}")
                
            print(f"\n✨ Configuration active: {active}")
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def create_configuration(self):
        """Crée une nouvelle configuration"""
        print("\n➕ Création d'une nouvelle configuration")
        print("-"*40)
        
        try:
            # Saisie des paramètres
            name = input("Nom de la configuration: ").strip()
            if not name:
                print("❌ Nom requis")
                return
                
            description = input("Description: ").strip()
            
            print("\nParamètres de mesure:")
            print("💡 Intensité: contrôle la puissance LED (0.0 = éteint, 1.0 = maximum)")
            intensity = float(input("Intensité (0.0-1.0) [défaut 0.5]: ") or 0.5)
            length = int(input("Nombre de points (1-2000) [défaut 100]: ") or 100)
            frequency = float(input("Fréquence Hz (1.0-200.0) [défaut 10.0]: ") or 10.0)
            
            persist_input = input("Persistante après redémarrage? (o/n) [défaut n]: ").strip().lower()
            persist = persist_input in ['o', 'oui', 'y', 'yes']
            
            # Validation des paramètres
            if not (0.0 <= intensity <= 1.0):
                print("❌ L'intensité doit être entre 0.0 et 1.0")
                return
            if not (1 <= length <= 2000):
                print("❌ Le nombre de points doit être entre 1 et 2000")
                return
            if not (1.0 <= frequency <= 200.0):
                print("❌ La fréquence doit être entre 1.0 et 200.0 Hz")
                return
            
            # Création de la config (SANS paramètre actinic)
            config = {
                "name": name,
                "description": description,
                "intensity": intensity,
                "length": length,
                "frequency": frequency,
                "persist": persist
            }
            
            # Affichage récapitulatif
            print(f"\n📋 Récapitulatif de la configuration:")
            print(f"   Nom: {name}")
            print(f"   Description: {description}")
            print(f"   Intensité LED: {intensity} ({intensity*100:.0f}%)")
            print(f"   Points de mesure: {length}")
            print(f"   Fréquence: {frequency} Hz")
            print(f"   Durée estimée: {length/frequency:.1f} secondes")
            print(f"   Persistante: {'Oui' if persist else 'Non'}")
            
            confirm = input("\nConfirmer la création? (o/n): ").strip().lower()
            if confirm not in ['o', 'oui', 'y', 'yes']:
                print("❌ Création annulée")
                return
            
            if self.sensor.create_config(config):
                print(f"✅ Configuration '{name}' créée avec succès")
                
                # Proposer de l'activer
                activate = input("\nActiver cette configuration? (o/n): ").strip().lower()
                if activate in ['o', 'oui', 'y', 'yes']:
                    if self.sensor.set_active_config(name):
                        print(f"🎯 Configuration '{name}' activée")
                    else:
                        print("❌ Erreur lors de l'activation")
            else:
                print("❌ Échec de la création")
                
        except ValueError as e:
            print(f"❌ Erreur de saisie: {e}")
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def modify_configuration(self):
        """Modifie une configuration existante"""
        print("\n✏️  Modification d'une configuration")
        print("-"*40)
        
        try:
            # Lister les configs personnalisées
            configs = self.sensor.list_configs()
            custom_configs = [c for c in configs if c not in ['default', 'quick', 'detailed', 'persist']]
            
            if not custom_configs:
                print("❌ Aucune configuration personnalisée à modifier")
                print("💡 Les configurations prédéfinies (default, quick, detailed, persist) ne peuvent pas être modifiées")
                input("\nAppuyez sur Entrée pour continuer...")
                return
            
            print("Configurations modifiables:")
            for i, config in enumerate(custom_configs, 1):
                print(f"{i}. {config}")
            
            choice = input("\nNuméro de la configuration à modifier: ").strip()
            try:
                index = int(choice) - 1
                config_name = custom_configs[index]
            except (ValueError, IndexError):
                print("❌ Choix invalide")
                return
            
            # Récupérer config actuelle
            current = self.sensor.get_config(config_name)
            if not current:
                print("❌ Configuration non trouvée")
                return
            
            print(f"\nConfiguration actuelle '{config_name}':")
            for key, value in current.items():
                if key != "name":
                    print(f"  {key}: {value}")
            
            print("\nNouvelles valeurs (Entrée = garder actuel):")
            
            # Modification interactive
            description = input(f"Description [{current.get('description', '')}]: ").strip()
            if not description:
                description = current.get('description', '')
            
            intensity_str = input(f"Intensité (0.0-1.0) [{current.get('intensity', 0.5)}]: ").strip()
            intensity = float(intensity_str) if intensity_str else current.get('intensity', 0.5)
            
            length_str = input(f"Nombre de points (1-2000) [{current.get('length', 100)}]: ").strip()
            length = int(length_str) if length_str else current.get('length', 100)
            
            frequency_str = input(f"Fréquence Hz (1.0-200.0) [{current.get('frequency', 10.0)}]: ").strip()
            frequency = float(frequency_str) if frequency_str else current.get('frequency', 10.0)
            
            persist_str = input(f"Persistante (o/n) [{'o' if current.get('persist', False) else 'n'}]: ").strip().lower()
            if persist_str:
                persist = persist_str in ['o', 'oui', 'y', 'yes']
            else:
                persist = current.get('persist', False)
            
            # Validation
            if not (0.0 <= intensity <= 1.0):
                print("❌ L'intensité doit être entre 0.0 et 1.0")
                return
            if not (1 <= length <= 2000):
                print("❌ Le nombre de points doit être entre 1 et 2000")
                return
            if not (1.0 <= frequency <= 200.0):
                print("❌ La fréquence doit être entre 1.0 et 200.0 Hz")
                return
            
            # Nouvelle config (SANS paramètre actinic)
            new_config = {
                "name": config_name,
                "description": description,
                "intensity": intensity,
                "length": length,
                "frequency": frequency,
                "persist": persist
            }
            
            # Affichage récapitulatif
            print(f"\n📋 Modifications:")
            print(f"   Intensité LED: {intensity} ({intensity*100:.0f}%)")
            print(f"   Points: {length}")
            print(f"   Fréquence: {frequency} Hz")
            print(f"   Durée estimée: {length/frequency:.1f} secondes")
            
            confirm = input("\nConfirmer les modifications? (o/n): ").strip().lower()
            if confirm not in ['o', 'oui', 'y', 'yes']:
                print("❌ Modification annulée")
                return
            
            if self.sensor.update_config(new_config):
                print(f"✅ Configuration '{config_name}' modifiée avec succès")
            else:
                print("❌ Échec de la modification")
                
        except ValueError as e:
            print(f"❌ Erreur de saisie: {e}")
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def delete_configuration(self):
        """Supprime une configuration"""
        print("\n🗑️  Suppression d'une configuration")
        print("-"*40)
        
        try:
            # Lister les configs personnalisées
            configs = self.sensor.list_configs()
            custom_configs = [c for c in configs if c not in ['default', 'quick', 'detailed', 'persist']]
            
            if not custom_configs:
                print("❌ Aucune configuration personnalisée à supprimer")
                print("💡 Les configurations prédéfinies ne peuvent pas être supprimées")
                input("\nAppuyez sur Entrée pour continuer...")
                return
            
            print("Configurations supprimables:")
            for i, config in enumerate(custom_configs, 1):
                print(f"{i}. {config}")
            
            choice = input("\nNuméro de la configuration à supprimer: ").strip()
            try:
                index = int(choice) - 1
                config_name = custom_configs[index]
            except (ValueError, IndexError):
                print("❌ Choix invalide")
                return
            
            print(f"\n⚠️  Attention: Vous allez supprimer définitivement la configuration '{config_name}'")
            confirm = input("Confirmer la suppression? (oui/non): ").strip().lower()
            
            if confirm not in ['oui', 'yes']:
                print("❌ Suppression annulée")
                return
            
            if self.sensor.delete_config(config_name):
                print(f"✅ Configuration '{config_name}' supprimée avec succès")
            else:
                print("❌ Échec de la suppression")
                
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def change_active_configuration(self):
        """Change la configuration active"""
        print("\n🎯 Changement de configuration active")
        print("-"*40)
        
        try:
            configs = self.sensor.list_configs()
            active = self.sensor.get_active_config()
            
            print("Configurations disponibles:")
            for i, config in enumerate(configs, 1):
                marker = "🎯" if config == active else "  "
                print(f"{marker} {i}. {config}")
            
            choice = input(f"\nNuméro de la nouvelle configuration active: ").strip()
            try:
                index = int(choice) - 1
                config_name = configs[index]
            except (ValueError, IndexError):
                print("❌ Choix invalide")
                return
            
            if config_name == active:
                print(f"💡 '{config_name}' est déjà la configuration active")
                return
            
            if self.sensor.set_active_config(config_name):
                print(f"✅ Configuration active changée vers '{config_name}'")
                
                # Afficher les détails de la nouvelle config
                details = self.sensor.get_active_config_details()
                if details:
                    print(f"\n📋 Détails de '{config_name}':")
                    print(f"   Intensité: {details.get('intensity', 'N/A')} ({details.get('intensity', 0)*100:.0f}%)")
                    print(f"   Points: {details.get('length', 'N/A')}")
                    print(f"   Fréquence: {details.get('frequency', 'N/A')} Hz")
                    print(f"   Durée estimée: {details.get('length', 0)/details.get('frequency', 1):.1f}s")
            else:
                print("❌ Échec du changement de configuration")
                
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def show_active_config_details(self):
        """Affiche les détails de la configuration active"""
        print("\n📄 Détails de la configuration active")
        print("-"*50)
        
        try:
            active_name = self.sensor.get_active_config()
            details = self.sensor.get_active_config_details()
            
            if details:
                print(f"🎯 Configuration: {active_name}")
                print(f"📝 Description: {details.get('description', 'Aucune description')}")
                print(f"💡 Intensité LED: {details.get('intensity', 'N/A')} ({details.get('intensity', 0)*100:.0f}%)")
                print(f"📊 Points de mesure: {details.get('length', 'N/A')}")
                print(f"⚡ Fréquence: {details.get('frequency', 'N/A')} Hz")
                print(f"⏱️  Durée estimée: {details.get('length', 0)/details.get('frequency', 1):.1f} secondes")
                print(f"💾 Persistante: {'Oui' if details.get('persist', False) else 'Non'}")
            else:
                print("❌ Impossible de récupérer les détails")
                
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    # =========================
    # MESURES DE FLUORESCENCE
    # =========================
    
    def manage_measurements(self):
        """Menu de gestion des mesures"""
        while True:
            options = {
                "1": "🔬 Mesure avec config active",
                "2": "⚙️  Mesure avec paramètres personnalisés",
                "3": "🔄 Mesure en série",
                "4": "📊 Afficher dernière mesure",
                "5": "📋 Historique des mesures",
                "6": "🔌 Vérifier statut du capteur",
                "r": "🔙 Retour menu principal"
            }
            
            self.print_menu("MESURES DE FLUORESCENCE", options)
            choice = self.get_user_choice("Votre choix: ", ["1", "2", "3", "4", "5", "6", "r"])
            
            if choice == "1":
                self.measure_with_active_config()
            elif choice == "2":
                self.measure_with_custom_params()
            elif choice == "3":
                self.series_measurement()
            elif choice == "4":
                self.show_last_measurement()
            elif choice == "5":
                self.show_measurement_history()
            elif choice == "6":
                self.check_sensor_status()
            elif choice == "r":
                break
    
    def measure_with_active_config(self):
        """Effectue une mesure avec la configuration active"""
        print("\n🔬 Mesure avec configuration active")
        print("-"*40)
        
        try:
            # Afficher config active
            active_name = self.sensor.get_active_config()
            details = self.sensor.get_active_config_details()
            
            if not details:
                print("❌ Impossible de récupérer la configuration active")
                input("\nAppuyez sur Entrée pour continuer...")
                return
            
            print(f"🎯 Configuration: {active_name}")
            print(f"💡 Intensité: {details.get('intensity', 'N/A')} ({details.get('intensity', 0)*100:.0f}%)")
            print(f"📊 Points: {details.get('length', 'N/A')}")
            print(f"⚡ Fréquence: {details.get('frequency', 'N/A')} Hz")
            estimated_time = details.get('length', 0) / details.get('frequency', 1)
            print(f"⏱️  Durée estimée: {estimated_time:.1f} secondes")
            
            # Confirmation
            proceed = input(f"\nLancer la mesure? (o/n): ").strip().lower()
            if proceed not in ['o', 'oui', 'y', 'yes']:
                print("❌ Mesure annulée")
                return
            
            # Mesure
            print(f"\n🔄 Mesure en cours... (durée: ~{estimated_time:.1f}s)")
            start_time = time.time()
            
            measurements = self.sensor.measure()
            
            elapsed = time.time() - start_time
            
            if measurements:
                print(f"✅ Mesure terminée en {elapsed:.1f}s")
                print(f"📊 {len(measurements)} points acquis")
                
                # Statistiques rapides
                avg_val = sum(measurements) / len(measurements)
                min_val = min(measurements)
                max_val = max(measurements)
                
                print(f"\n📈 Statistiques:")
                print(f"   Moyenne: {avg_val:.6f}")
                print(f"   Minimum: {min_val:.6f}")
                print(f"   Maximum: {max_val:.6f}")
                print(f"   Plage: {max_val - min_val:.6f}")
                
                # Sauvegarder en historique
                measurement_data = {
                    'timestamp': datetime.now(),
                    'config_name': active_name,
                    'config_details': details,
                    'data': measurements,
                    'stats': {
                        'count': len(measurements),
                        'mean': avg_val,
                        'min': min_val,
                        'max': max_val,
                        'duration': elapsed
                    }
                }
                
                self.last_measurement = measurement_data
                self.last_config_used = active_name
                self.measurement_history.append(measurement_data)
                
                print(f"\n💾 Mesure ajoutée à l'historique ({len(self.measurement_history)} total)")
                
            else:
                print("❌ Aucune donnée reçue")
                
        except Exception as e:
            print(f"❌ Erreur pendant la mesure: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def measure_with_custom_params(self):
        """Effectue une mesure avec des paramètres personnalisés"""
        print("\n⚙️  Mesure avec paramètres personnalisés")
        print("-"*50)
        
        try:
            # Récupération des paramètres personnalisés (SANS actinic)
            print("🔧 Paramètres de mesure:")
            print("💡 Intensité: puissance LED (0.0 = éteint, 1.0 = maximum)")
            
            intensity = float(input("Intensité (0.0-1.0) [défaut 0.5]: ") or 0.5)
            length = int(input("Nombre de points (1-2000) [défaut 100]: ") or 100)
            frequency = float(input("Fréquence Hz (1.0-200.0) [défaut 10.0]: ") or 10.0)
            persist = input("Sauvegarde persistante? (o/n) [défaut n]: ").strip().lower() in ['o', 'oui', 'y', 'yes']
            
            # Validation des paramètres
            if not (0.0 <= intensity <= 1.0):
                print("❌ L'intensité doit être entre 0.0 et 1.0")
                return
            if not (1 <= length <= 2000):
                print("❌ Le nombre de points doit être entre 1 et 2000")
                return
            if not (1.0 <= frequency <= 200.0):
                print("❌ La fréquence doit être entre 1.0 et 200.0 Hz")
                return
            
            estimated_time = length / frequency
            
            # Récapitulatif
            print(f"\n📋 Récapitulatif:")
            print(f"   💡 Intensité LED: {intensity} ({intensity*100:.0f}%)")
            print(f"   📊 Points: {length}")
            print(f"   ⚡ Fréquence: {frequency} Hz")
            print(f"   ⏱️  Durée estimée: {estimated_time:.1f} secondes")
            print(f"   💾 Persistante: {'Oui' if persist else 'Non'}")
            
            # Confirmation
            proceed = input(f"\nLancer la mesure? (o/n): ").strip().lower()
            if proceed not in ['o', 'oui', 'y', 'yes']:
                print("❌ Mesure annulée")
                return
            
            # Mesure
            print(f"\n🔄 Mesure en cours... (durée: ~{estimated_time:.1f}s)")
            start_time = time.time()
            
            measurements = self.sensor.measure_with_params(
                intensity=intensity,
                length=length,
                frequency=frequency,
                persist=persist
            )
            
            elapsed = time.time() - start_time
            
            if measurements:
                print(f"✅ Mesure terminée en {elapsed:.1f}s")
                print(f"📊 {len(measurements)} points acquis")
                
                # Statistiques
                avg_val = sum(measurements) / len(measurements)
                min_val = min(measurements)
                max_val = max(measurements)
                
                print(f"\n📈 Statistiques:")
                print(f"   Moyenne: {avg_val:.6f}")
                print(f"   Minimum: {min_val:.6f}")
                print(f"   Maximum: {max_val:.6f}")
                print(f"   Plage: {max_val - min_val:.6f}")
                
                # Sauvegarder en historique
                measurement_data = {
                    'timestamp': datetime.now(),
                    'config_name': 'custom',
                    'config_details': {
                        'intensity': intensity,
                        'length': length,
                        'frequency': frequency,
                        'persist': persist
                    },
                    'data': measurements,
                    'stats': {
                        'count': len(measurements),
                        'mean': avg_val,
                        'min': min_val,
                        'max': max_val,
                        'duration': elapsed
                    }
                }
                
                self.last_measurement = measurement_data
                self.last_config_used = 'custom'
                self.measurement_history.append(measurement_data)
                
                print(f"\n💾 Mesure ajoutée à l'historique ({len(self.measurement_history)} total)")
                
            else:
                print("❌ Aucune donnée reçue")
                
        except ValueError as e:
            print(f"❌ Erreur de saisie: {e}")
        except Exception as e:
            print(f"❌ Erreur pendant la mesure: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def series_measurement(self):
        """Effectue une série de mesures automatiques"""
        print("\n🔄 Mesures en série")
        print("-"*30)
        
        try:
            # Configuration de la série
            count = int(input("Nombre de mesures à effectuer [défaut 3]: ") or 3)
            delay = float(input("Délai entre mesures en secondes [défaut 5.0]: ") or 5.0)
            
            if count < 1 or count > 20:
                print("❌ Le nombre de mesures doit être entre 1 et 20")
                return
            if delay < 0:
                print("❌ Le délai doit être positif")
                return
            
            # Config active pour la série
            active_name = self.sensor.get_active_config()
            details = self.sensor.get_active_config_details()
            
            if not details:
                print("❌ Configuration active non disponible")
                return
            
            estimated_per_measure = details.get('length', 100) / details.get('frequency', 10)
            total_time = count * (estimated_per_measure + delay) - delay
            
            print(f"\n📋 Configuration de la série:")
            print(f"   🎯 Configuration: {active_name}")
            print(f"   🔢 Nombre de mesures: {count}")
            print(f"   ⏱️  Délai entre mesures: {delay}s")
            print(f"   📊 Durée par mesure: ~{estimated_per_measure:.1f}s")
            print(f"   ⏰ Durée totale estimée: ~{total_time:.1f}s")
            
            proceed = input(f"\nLancer la série de {count} mesures? (o/n): ").strip().lower()
            if proceed not in ['o', 'oui', 'y', 'yes']:
                print("❌ Série annulée")
                return
            
            # Exécution de la série
            series_results = []
            print(f"\n🚀 Début de la série de {count} mesures...")
            
            for i in range(count):
                print(f"\n📊 Mesure {i+1}/{count}")
                print("-" * 20)
                
                start_time = time.time()
                measurements = self.sensor.measure()
                elapsed = time.time() - start_time
                
                if measurements:
                    avg_val = sum(measurements) / len(measurements)
                    print(f"✅ Mesure {i+1} terminée: {len(measurements)} points, moyenne: {avg_val:.6f}")
                    
                    # Sauvegarder
                    measurement_data = {
                        'timestamp': datetime.now(),
                        'config_name': active_name,
                        'config_details': details,
                        'data': measurements,
                        'series_info': {
                            'series_number': i+1,
                            'total_in_series': count
                        },
                        'stats': {
                            'count': len(measurements),
                            'mean': avg_val,
                            'min': min(measurements),
                            'max': max(measurements),
                            'duration': elapsed
                        }
                    }
                    
                    series_results.append(measurement_data)
                    self.measurement_history.append(measurement_data)
                    
                    # Attendre entre les mesures (sauf la dernière)
                    if i < count - 1:
                        print(f"⏳ Attente de {delay}s avant la mesure suivante...")
                        time.sleep(delay)
                else:
                    print(f"❌ Mesure {i+1} échouée - aucune donnée reçue")
            
            # Résumé de la série
            print(f"\n🏁 Série terminée!")
            print(f"📊 {len(series_results)}/{count} mesures réussies")
            
            if series_results:
                means = [result['stats']['mean'] for result in series_results]
                series_avg = sum(means) / len(means)
                series_std = np.std(means) if len(means) > 1 else 0
                
                print(f"\n📈 Statistiques de la série:")
                print(f"   Moyenne des moyennes: {series_avg:.6f}")
                print(f"   Écart-type des moyennes: {series_std:.6f}")
                print(f"   Min des moyennes: {min(means):.6f}")
                print(f"   Max des moyennes: {max(means):.6f}")
                
                self.last_measurement = series_results[-1]  # Dernière mesure
                
        except ValueError as e:
            print(f"❌ Erreur de saisie: {e}")
        except Exception as e:
            print(f"❌ Erreur pendant la série: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def show_last_measurement(self):
        """Affiche les détails de la dernière mesure"""
        if not self.last_measurement:
            print("\n❌ Aucune mesure disponible")
            input("\nAppuyez sur Entrée pour continuer...")
            return
        
        print("\n📊 Dernière mesure")
        print("-"*40)
        
        try:
            last = self.last_measurement
            
            print(f"🕒 Horodatage: {last['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🎯 Configuration: {last['config_name']}")
            
            config = last['config_details']
            print(f"💡 Intensité: {config.get('intensity', 'N/A')} ({config.get('intensity', 0)*100:.0f}%)")
            print(f"📊 Points: {config.get('length', 'N/A')}")
            print(f"⚡ Fréquence: {config.get('frequency', 'N/A')} Hz")
            
            stats = last['stats']
            print(f"\n📈 Statistiques:")
            print(f"   Points acquis: {stats['count']}")
            print(f"   Moyenne: {stats['mean']:.6f}")
            print(f"   Minimum: {stats['min']:.6f}")
            print(f"   Maximum: {stats['max']:.6f}")
            print(f"   Plage: {stats['max'] - stats['min']:.6f}")
            print(f"   Durée: {stats['duration']:.1f}s")
            
            if 'series_info' in last:
                series = last['series_info']
                print(f"\n🔄 Info série:")
                print(f"   Mesure {series['series_number']}/{series['total_in_series']}")
            
            # Affichage de quelques valeurs
            data = last['data']
            print(f"\n🔬 Échantillon des données (10 premiers points):")
            for i, value in enumerate(data[:10]):
                print(f"   Point {i+1}: {value:.6f}")
            
            if len(data) > 10:
                print(f"   ... et {len(data)-10} points supplémentaires")
                
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def show_measurement_history(self):
        """Affiche l'historique des mesures"""
        if not self.measurement_history:
            print("\n❌ Aucune mesure dans l'historique")
            input("\nAppuyez sur Entrée pour continuer...")
            return
        
        print(f"\n📋 Historique des mesures ({len(self.measurement_history)} total)")
        print("-"*80)
        
        try:
            # Afficher les 10 dernières mesures
            recent = self.measurement_history[-10:]
            
            print("🕒 Horodatage        🎯 Config    📊 Points   📈 Moyenne      ⏱️  Durée")
            print("-"*80)
            
            for i, measurement in enumerate(recent):
                timestamp = measurement['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                config_name = measurement['config_name'][:12]  # Tronquer si trop long
                stats = measurement['stats']
                
                print(f"{timestamp} {config_name:<12} {stats['count']:>7} "
                      f"{stats['mean']:>11.6f} {stats['duration']:>7.1f}s")
            
            if len(self.measurement_history) > 10:
                print(f"\n💡 Affichage des 10 dernières mesures sur {len(self.measurement_history)} total")
                
            # Statistiques globales
            all_means = [m['stats']['mean'] for m in self.measurement_history]
            all_counts = [m['stats']['count'] for m in self.measurement_history]
            
            print(f"\n📈 Statistiques globales:")
            print(f"   Nombre total de mesures: {len(self.measurement_history)}")
            print(f"   Total de points acquis: {sum(all_counts)}")
            print(f"   Moyenne des moyennes: {sum(all_means)/len(all_means):.6f}")
            print(f"   Écart-type des moyennes: {np.std(all_means):.6f}")
            
            # Configurations utilisées
            configs_used = set(m['config_name'] for m in self.measurement_history)
            print(f"   Configurations utilisées: {', '.join(configs_used)}")
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def check_sensor_status(self):
        """Vérifie le statut du capteur"""
        print("\n🔌 Statut du capteur")
        print("-"*30)
        
        try:
            status = self.sensor.get_device_status()
            
            if status['connected']:
                print("✅ Capteur connecté et opérationnel")
                print(f"📡 Statut: {status['status']}")
                
                # Informations supplémentaires
                configs = self.sensor.list_configs()
                active = self.sensor.get_active_config()
                
                print(f"\n📋 Informations du système:")
                print(f"   🎯 Configuration active: {active}")
                print(f"   📊 Configurations disponibles: {len(configs)}")
                print(f"   💾 Mesures en historique: {len(self.measurement_history)}")
                
            else:
                print("❌ Capteur non connecté ou non répondant")
                print(f"📡 Statut: {status['status']}")
                print("\n🔧 Actions suggérées:")
                print("   - Vérifier les connexions physiques")
                print("   - Redémarrer l'application serveur sur Pi0")
                print("   - Vérifier l'alimentation du capteur")
                
        except Exception as e:
            print(f"❌ Erreur de communication: {e}")
            print("\n🔧 Actions suggérées:")
            print("   - Vérifier la connexion réseau avec Pi0")
            print("   - Redémarrer le service RCom")
            
        input("\nAppuyez sur Entrée pour continuer...")
    
    # =========================
    # SAUVEGARDE ET EXPORT
    # =========================
    
    def manage_data_export(self):
        """Menu de gestion des données"""
        while True:
            options = {
                "1": "💾 Sauvegarder dernière mesure",
                "2": "📊 Exporter historique complet",
                "3": "📈 Créer graphique",
                "4": "📋 Analyser et exporter stats",
                "5": "🗂️  Voir fichiers sauvegardés",
                "r": "🔙 Retour menu principal"
            }
            
            self.print_menu("SAUVEGARDE ET EXPORT", options)
            choice = self.get_user_choice("Votre choix: ", ["1", "2", "3", "4", "5", "r"])
            
            if choice == "1":
                self.save_last_measurement()
            elif choice == "2":
                self.export_full_history()
            elif choice == "3":
                self.create_plot()
            elif choice == "4":
                self.analyze_and_export_stats()
            elif choice == "5":
                self.show_saved_files()
            elif choice == "r":
                break
    
    def save_last_measurement(self):
        """Sauvegarde la dernière mesure"""
        if not self.last_measurement:
            print("\n❌ Aucune mesure à sauvegarder")
            input("\nAppuyez sur Entrée pour continuer...")
            return
        
        timestamp = self.last_measurement['timestamp']
        config_name = self.last_measurement['config_name']
        
        base_filename = f"fluo_{config_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        print("\n💾 Sauvegarde de la dernière mesure")
        print("-"*40)
        print(f"📊 Configuration: {config_name}")
        print(f"🕒 Horodatage: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📈 Points: {len(self.last_measurement['data'])}")
        
        # Choix du format
        print("\n📋 Formats disponibles:")
        print("1. JSON (métadonnées + données)")
        print("2. CSV (données uniquement)")  
        print("3. NumPy (.npz) - format binaire")
        print("4. Tous les formats")
        
        format_choice = self.get_user_choice("Format de sauvegarde (1-4): ", ["1", "2", "3", "4"])
        
        try:
            saved_files = []
            
            if format_choice in ["1", "4"]:
                # Sauvegarde JSON
                json_filename = f"{base_filename}.json"
                json_filepath = os.path.join(self.output_dir, json_filename)
                
                with open(json_filepath, 'w') as f:
                    # Convertir datetime en string pour JSON
                    json_data = dict(self.last_measurement)
                    json_data['timestamp'] = timestamp.isoformat()
                    json.dump(json_data, f, indent=2)
                
                saved_files.append(json_filepath)
            
            if format_choice in ["2", "4"]:
                # Sauvegarde CSV
                csv_filename = f"{base_filename}.csv"
                csv_filepath = os.path.join(self.output_dir, csv_filename)
                
                with open(csv_filepath, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Point', 'Fluorescence'])
                    for i, value in enumerate(self.last_measurement['data']):
                        writer.writerow([i+1, value])
                
                saved_files.append(csv_filepath)
            
            if format_choice in ["3", "4"]:
                # Sauvegarde NumPy
                npz_filename = f"{base_filename}.npz"
                npz_filepath = os.path.join(self.output_dir, npz_filename)
                
                np.savez(npz_filepath,
                        data=np.array(self.last_measurement['data']),
                        config=self.last_measurement['config_details'],
                        stats=self.last_measurement['stats'],
                        timestamp=timestamp.isoformat())
                
                saved_files.append(npz_filepath)
            
            print(f"\n✅ Sauvegarde terminée:")
            for filepath in saved_files:
                size = os.path.getsize(filepath)
                print(f"   📁 {os.path.basename(filepath)} ({size} bytes)")
                
        except Exception as e:
            print(f"❌ Erreur de sauvegarde: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def export_full_history(self):
        """Export complet de l'historique"""
        if not self.measurement_history:
            print("\n❌ Aucune mesure dans l'historique")
            input("\nAppuyez sur Entrée pour continuer...")
            return
        
        timestamp = datetime.now()
        base_filename = f"fluorescence_history_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        print(f"\n📊 Export de l'historique complet")
        print("-"*40)
        print(f"📈 Nombre de mesures: {len(self.measurement_history)}")
        
        try:
            # Export JSON complet
            json_filename = f"{base_filename}.json"
            json_filepath = os.path.join(self.output_dir, json_filename)
            
            export_data = {
                'export_info': {
                    'timestamp': timestamp.isoformat(),
                    'measurement_count': len(self.measurement_history),
                    'exported_by': 'ROMI Fluorescence App'
                },
                'measurements': []
            }
            
            for measurement in self.measurement_history:
                # Convertir pour JSON
                json_measurement = dict(measurement)
                json_measurement['timestamp'] = measurement['timestamp'].isoformat()
                export_data['measurements'].append(json_measurement)
            
            with open(json_filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            # Export CSV résumé
            csv_filename = f"{base_filename}_summary.csv"
            csv_filepath = os.path.join(self.output_dir, csv_filename)
            
            with open(csv_filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Config', 'Points', 'Mean', 'Min', 'Max', 'Duration'])
                
                for measurement in self.measurement_history:
                    timestamp_str = measurement['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    stats = measurement['stats']
                    writer.writerow([
                        timestamp_str,
                        measurement['config_name'],
                        stats['count'],
                        stats['mean'],
                        stats['min'],
                        stats['max'],
                        stats['duration']
                    ])
            
            json_size = os.path.getsize(json_filepath)
            csv_size = os.path.getsize(csv_filepath)
            
            print(f"\n✅ Export terminé:")
            print(f"   📁 {os.path.basename(json_filepath)} ({json_size} bytes)")
            print(f"   📁 {os.path.basename(csv_filepath)} ({csv_size} bytes)")
            
        except Exception as e:
            print(f"❌ Erreur d'export: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def create_plot(self):
        """Crée un graphique de la dernière mesure"""
        if not MATPLOTLIB_AVAILABLE:
            print("\n❌ matplotlib non disponible")
            print("   Installez matplotlib pour cette fonctionnalité")
            input("\nAppuyez sur Entrée pour continuer...")
            return
        
        if not self.last_measurement:
            print("\n❌ Aucune mesure à tracer")
            input("\nAppuyez sur Entrée pour continuer...")
            return
        
        timestamp = self.last_measurement['timestamp']
        config_name = self.last_measurement['config_name']
        data = self.last_measurement['data']
        
        filename = f"fluo_plot_{config_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(self.output_dir, filename)
        
        print(f"\n📈 Création du graphique")
        print("-"*30)
        
        try:
            plt.figure(figsize=(12, 6))
            plt.plot(data, 'b-', linewidth=1, alpha=0.8)
            plt.title(f'Fluorescence - {config_name}\n{timestamp.strftime("%Y-%m-%d %H:%M:%S")}', fontsize=14)
            plt.xlabel('Point de mesure', fontsize=12)
            plt.ylabel('Intensité de fluorescence', fontsize=12)
            
            # Statistiques
            avg_val = sum(data) / len(data)
            plt.axhline(y=avg_val, color='green', linestyle='--', alpha=0.8, label=f'Moyenne: {avg_val:.6f}')
            
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            # Sauvegarde
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()  # Fermer pour libérer la mémoire
            
            print(f"\n✅ Graphique sauvegardé:")
            print(f"   📁 {filepath}")
            
        except Exception as e:
            print(f"❌ Erreur de sauvegarde: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def analyze_and_export_stats(self):
        """Analyse et exporte les statistiques"""
        if not self.measurement_history:
            print("❌ Aucune mesure dans l'historique")
            input("\nAppuyez sur Entrée pour continuer...")
            return
        
        timestamp = datetime.now()
        filename = f"fluorescence_stats_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            # Calcul des statistiques globales
            all_means = []
            all_stds = []
            config_stats = {}
            
            for measurement in self.measurement_history:
                data = measurement['data']
                mean_val = np.mean(data)
                std_val = np.std(data)
                
                all_means.append(mean_val)
                all_stds.append(std_val)
                
                config_name = measurement['config_name']
                if config_name not in config_stats:
                    config_stats[config_name] = []
                config_stats[config_name].append(mean_val)
            
            # Compilation des stats
            stats = {
                'analysis_info': {
                    'timestamp': timestamp.isoformat(),
                    'total_measurements': len(self.measurement_history),
                    'analysis_period': {
                        'start': self.measurement_history[0]['timestamp'].isoformat(),
                        'end': self.measurement_history[-1]['timestamp'].isoformat()
                    }
                },
                'global_statistics': {
                    'mean_of_means': float(np.mean(all_means)),
                    'std_of_means': float(np.std(all_means)),
                    'min_mean': float(np.min(all_means)),
                    'max_mean': float(np.max(all_means)),
                    'avg_std': float(np.mean(all_stds))
                },
                'per_configuration': {}
            }
            
            # Stats par configuration
            for config, means in config_stats.items():
                stats['per_configuration'][config] = {
                    'measurement_count': len(means),
                    'mean_avg': float(np.mean(means)),
                    'mean_std': float(np.std(means)),
                    'mean_min': float(np.min(means)),
                    'mean_max': float(np.max(means))
                }
            
            # Sauvegarde
            with open(filepath, 'w') as f:
                json.dump(stats, f, indent=2)
            
            print(f"\n📊 Analyse statistique terminée:")
            print(f"   📁 {filepath}")
            print(f"   📈 {len(self.measurement_history)} mesures analysées")
            print(f"   🎯 {len(config_stats)} configurations utilisées")
            print(f"   📋 Moyenne globale: {stats['global_statistics']['mean_of_means']:.6f}")
            
        except Exception as e:
            print(f"❌ Erreur d'analyse: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    def show_saved_files(self):
        """Affiche les fichiers sauvegardés"""
        print("\n🗂️  Fichiers sauvegardés")
        print("-"*50)
        
        try:
            files = os.listdir(self.output_dir)
            files.sort()
            
            if not files:
                print("❌ Aucun fichier sauvegardé")
            else:
                print(f"Dossier: {self.output_dir}")
                print()
                
                for file in files:
                    filepath = os.path.join(self.output_dir, file)
                    size = os.path.getsize(filepath)
                    
                    # Déterminer le type
                    if file.endswith('.json'):
                        icon = "📋"
                    elif file.endswith('.csv'):
                        icon = "📊"
                    elif file.endswith('.npz'):
                        icon = "🔬"
                    elif file.endswith('.png'):
                        icon = "📈"
                    else:
                        icon = "📄"
                    
                    print(f"{icon} {file:40s} ({size:6d} bytes)")
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")
    
    # =========================
    # MENU PRINCIPAL
    # =========================
    
    def run(self):
        """Lance l'application principale"""
        if not self.connect_sensor():
            return
        
        while True:
            options = {
                "1": "⚙️  Gestion des configurations",
                "2": "🔬 Mesures de fluorescence",
                "3": "💾 Sauvegarde et export",
                "4": "📊 Statut du système",
                "q": "🚪 Quitter"
            }
            
            self.print_menu("MENU PRINCIPAL", options)
            choice = self.get_user_choice("Votre choix: ", ["1", "2", "3", "4", "q"])
            
            if choice == "1":
                self.manage_configurations()
            elif choice == "2":
                self.manage_measurements()
            elif choice == "3":
                self.manage_data_export()
            elif choice == "4":
                self.show_system_status()
            elif choice == "q":
                break
        
        print("\n👋 Au revoir !")
    
    def show_system_status(self):
        """Affiche le statut du système"""
        print("\n📊 Statut du système")
        print("-"*40)
        
        try:
            # Info capteur
            configs = self.sensor.list_configs()
            active = self.sensor.get_active_config()
            
            print(f"🔌 Capteur: Connecté")
            print(f"🎯 Configuration active: {active}")
            print(f"📋 Configurations disponibles: {len(configs)}")
            print(f"📊 Mesures en mémoire: {len(self.measurement_history)}")
            
            if self.last_measurement:
                last_time = self.last_measurement['timestamp']
                print(f"🕒 Dernière mesure: {last_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Info fichiers
            files = os.listdir(self.output_dir)
            print(f"💾 Fichiers sauvegardés: {len(files)}")
            
            print(f"📁 Dossier de sortie: {self.output_dir}")
            print(f"📈 Matplotlib: {'Disponible' if MATPLOTLIB_AVAILABLE else 'Non disponible'}")
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        input("\nAppuyez sur Entrée pour continuer...")

# =========================
# POINT D'ENTRÉE
# =========================

def main():
    """Point d'entrée principal"""
    try:
        app = FluorescenceApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\n👋 Application interrompue par l'utilisateur")
    except Exception as e:
        print(f"\n💥 Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
