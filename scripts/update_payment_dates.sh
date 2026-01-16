#!/bin/bash
# Script pour mettre à jour les dates de paiement/versement
# Exécuté automatiquement chaque jour à 4h du matin

# Définir le répertoire de travail
cd /opt/budgeefamily

# Activer l'environnement virtuel
source .venv/bin/activate

# Définir les variables d'environnement Flask
export FLASK_APP=wsgi.py

# Exécuter la commande Flask
flask update-payment-dates

# Déconnecter
deactivate

# Log avec timestamp
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Mise à jour des dates de paiement effectuée" >> /opt/budgeefamily/logs/cron.log
