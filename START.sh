#!/bin/bash

# Script de lancement rapide de Subly Cloud

echo "🚀 Lancement de Subly Cloud..."
echo ""

# Activer l'environnement virtuel
source .venv/bin/activate

# Afficher l'URL
echo "✅ Application démarrée !"
echo ""
echo "📍 URL : http://localhost:5000"
echo ""
echo "Pour arrêter l'application, appuyez sur Ctrl+C"
echo ""

# Lancer l'application
python run.py
