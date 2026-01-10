.PHONY: help install init run clean test migrate upgrade

help:
	@echo "Commandes disponibles pour Subly Cloud:"
	@echo ""
	@echo "  make install    - Installer les dépendances"
	@echo "  make init       - Initialiser la base de données"
	@echo "  make run        - Lancer l'application"
	@echo "  make clean      - Nettoyer les fichiers temporaires"
	@echo "  make migrate    - Créer une migration"
	@echo "  make upgrade    - Appliquer les migrations"
	@echo "  make shell      - Ouvrir le shell Flask"
	@echo "  make admin      - Créer un utilisateur admin"
	@echo ""

install:
	@echo "Installation des dépendances..."
	pip install -r requirements.txt
	@echo "✅ Dépendances installées"

init:
	@echo "Initialisation de la base de données..."
	python init_db.py
	@echo "✅ Base de données initialisée"

run:
	@echo "Lancement de l'application..."
	python run.py

clean:
	@echo "Nettoyage des fichiers temporaires..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	@echo "✅ Nettoyage terminé"

migrate:
	@echo "Création d'une migration..."
	flask db migrate -m "$(MSG)"

upgrade:
	@echo "Application des migrations..."
	flask db upgrade

shell:
	@echo "Ouverture du shell Flask..."
	flask shell

admin:
	@echo "Création d'un utilisateur admin..."
	python create_admin.py

dev:
	@echo "Mode développement avec rechargement automatique..."
	FLASK_DEBUG=1 python run.py

test:
	@echo "Exécution des tests..."
	@echo "⚠️  Les tests ne sont pas encore implémentés"

setup: install init
	@echo "✅ Configuration terminée !"
	@echo "Lancez 'make run' pour démarrer l'application"
