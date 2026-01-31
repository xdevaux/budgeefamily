#!/bin/bash
# Script pour créer une sauvegarde automatique
# Exécuté automatiquement chaque jour à 3h du matin

# Définir le répertoire de travail
cd /opt/budgeefamily

# Activer l'environnement virtuel
source .venv/bin/activate

# Définir les variables d'environnement Flask
export FLASK_APP=wsgi.py

# Exécuter la commande Flask
flask auto-backup

# Déconnecter
deactivate

# Log avec timestamp
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Sauvegarde automatique effectuée" >> /opt/budgeefamily/logs/cron.log
