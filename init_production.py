#!/usr/bin/env python3
"""
Script d'initialisation complet pour la production
Crée les plans de base et l'utilisateur administrateur
"""

from app import create_app, db
from app.models import User, Plan
import os
from datetime import datetime


def init_plans():
    """Initialise les plans de base s'ils n'existent pas"""
    print("\n=== Initialisation des plans ===\n")

    plans_data = [
        {
            'name': 'Free',
            'price': 0.0,
            'currency': 'EUR',
            'billing_period': 'monthly',
            'max_subscriptions': 5,
            'description': 'Plan gratuit - Maximum 5 abonnements',
            'features': ['5 abonnements maximum', 'Catégories par défaut', 'Statistiques de base', 'Notifications'],
            'is_active': True
        },
        {
            'name': 'Premium',
            'price': 9.99,
            'currency': 'EUR',
            'billing_period': 'monthly',
            'max_subscriptions': None,
            'description': 'Plan Premium mensuel - Abonnements illimités',
            'features': ['Abonnements illimités', 'Catégories personnalisées', 'Services personnalisés', 'Statistiques avancées', 'Export des données'],
            'is_active': True
        },
        {
            'name': 'Premium Annual',
            'price': 99.90,
            'currency': 'EUR',
            'billing_period': 'yearly',
            'max_subscriptions': None,
            'description': 'Plan Premium annuel - Économisez 2 mois',
            'features': ['Abonnements illimités', 'Catégories personnalisées', 'Services personnalisés', 'Statistiques avancées', 'Export des données', 'Support prioritaire'],
            'is_active': True
        }
    ]

    created_plans = []
    existing_plans = []

    for plan_data in plans_data:
        existing_plan = Plan.query.filter_by(name=plan_data['name']).first()

        if existing_plan:
            existing_plans.append(plan_data['name'])
            print(f"ℹ️  Plan '{plan_data['name']}' existe déjà.")
        else:
            new_plan = Plan(**plan_data)
            db.session.add(new_plan)
            created_plans.append(plan_data['name'])
            print(f"✅ Plan '{plan_data['name']}' créé.")

    if created_plans:
        db.session.commit()
        print(f"\n✅ {len(created_plans)} plan(s) créé(s) : {', '.join(created_plans)}")

    if existing_plans:
        print(f"ℹ️  {len(existing_plans)} plan(s) existant(s) : {', '.join(existing_plans)}")

    return True


def init_admin():
    """Initialise l'utilisateur administrateur"""
    print("\n=== Initialisation de l'administrateur ===\n")

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

    # Récupérer le plan Premium
    premium_plan = Plan.query.filter_by(name='Premium').first()

    if not premium_plan:
        print("❌ ERREUR: Plan Premium introuvable. Exécutez d'abord l'initialisation des plans.")
        return False

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

    return True


def main():
    """Fonction principale d'initialisation"""
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("  INITIALISATION DE L'APPLICATION SUBLY CLOUD - PRODUCTION")
        print("=" * 60)

        # Initialiser les plans
        if not init_plans():
            print("\n❌ Erreur lors de l'initialisation des plans.")
            return False

        # Initialiser l'administrateur
        if not init_admin():
            print("\n❌ Erreur lors de l'initialisation de l'administrateur.")
            return False

        print("\n" + "=" * 60)
        print("  ✅ INITIALISATION TERMINÉE AVEC SUCCÈS")
        print("=" * 60)
        print("\n⚠️  IMPORTANT :")
        print("   - Conservez le mot de passe administrateur en lieu sûr")
        print("   - Changez le mot de passe après la première connexion")
        print("   - Ne partagez jamais vos identifiants admin\n")

        return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
