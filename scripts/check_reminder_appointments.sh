#!/bin/bash
# Script pour vérifier les rappels de rendez-vous et générer les notifications
# Exécuté automatiquement chaque jour à 8h du matin

# Définir le répertoire de travail
cd /opt/budgeefamily

# Activer l'environnement virtuel
source .venv/bin/activate

# Définir les variables d'environnement Flask
export FLASK_APP=wsgi.py

# Exécuter la commande Flask
flask check-reminder-appointments

# Déconnecter
deactivate

# Log avec timestamp
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Vérification des rappels de rendez-vous effectuée" >> /opt/budgeefamily/logs/cron.log
