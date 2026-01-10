#!/usr/bin/env python3
"""
Script d'initialisation pour créer l'utilisateur administrateur
À exécuter lors du déploiement en production
"""

from app import create_app, db
from app.models import User, Plan
import os
from datetime import datetime


def init_admin():
    app = create_app()

    with app.app_context():
        print("=== Initialisation de l'administrateur ===\n")

        # Récupérer les informations depuis les variables d'environnement
        admin_email = os.getenv('ADMIN_EMAIL', 'contact@subly.cloud')
        admin_password = os.getenv('ADMIN_PASSWORD')
        admin_first_name = os.getenv('ADMIN_FIRST_NAME', 'Admin')
        admin_last_name = os.getenv('ADMIN_LAST_NAME', 'Subly Cloud')

        # Vérifier si le mot de passe est fourni
        if not admin_password:
            print("❌ ERREUR: La variable d'environnement ADMIN_PASSWORD n'est pas définie.")
            print("   Définissez-la avec : export ADMIN_PASSWORD='votre_mot_de_passe'")
            return False

        # Vérifier si l'utilisateur existe déjà
        existing_admin = User.query.filter_by(email=admin_email).first()

        if existing_admin:
            print(f"ℹ️  L'utilisateur {admin_email} existe déjà.")

            # Mettre à jour les droits admin si nécessaire
            if not existing_admin.is_admin:
                existing_admin.is_admin = True
                existing_admin.is_active = True
                db.session.commit()
                print(f"✅ Droits administrateur activés pour {admin_email}")
            else:
                print(f"✅ {admin_email} est déjà administrateur.")

            return True

        # Récupérer ou créer le plan Premium
        premium_plan = Plan.query.filter_by(name='Premium').first()

        if not premium_plan:
            print("⚠️  Plan Premium introuvable. Création du plan...")
            premium_plan = Plan(
                name='Premium',
                price=9.99,
                currency='EUR',
                billing_period='monthly',
                max_subscriptions=None,  # Illimité
                description='Plan Premium - Abonnements illimités',
                features=['Abonnements illimités', 'Catégories personnalisées', 'Services personnalisés', 'Statistiques avancées'],
                is_active=True
            )
            db.session.add(premium_plan)
            db.session.commit()
            print("✅ Plan Premium créé.")

        # Créer l'utilisateur administrateur
        admin_user = User(
            email=admin_email,
            first_name=admin_first_name,
            last_name=admin_last_name,
            plan=premium_plan,
            is_admin=True,
            is_active=True,
            email_verified=True,
            email_verified_at=datetime.utcnow()
        )
        admin_user.set_password(admin_password)

        db.session.add(admin_user)
        db.session.commit()

        print(f"\n✅ Administrateur créé avec succès !")
        print(f"   Email : {admin_email}")
        print(f"   Nom : {admin_first_name} {admin_last_name}")
        print(f"   Plan : {premium_plan.name}")
        print(f"   Administrateur : Oui")
        print(f"   Email vérifié : Oui")
        print(f"\n⚠️  IMPORTANT : Conservez le mot de passe en lieu sûr !")

        return True


if __name__ == '__main__':
    success = init_admin()
    exit(0 if success else 1)
