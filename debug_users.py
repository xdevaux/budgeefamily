#!/usr/bin/env python3
"""
Script de debug pour vérifier les utilisateurs et leur plan
"""

from app import create_app, db
from app.models import User, Plan


def debug_users():
    app = create_app()

    with app.app_context():
        print("=== Debug des utilisateurs ===\n")

        # Récupérer tous les utilisateurs
        users = User.query.all()

        print(f"Total utilisateurs : {len(users)}\n")

        for user in users:
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Nom: {user.first_name} {user.last_name}")
            print(f"Plan: {user.plan.name if user.plan else 'AUCUN (NULL)'}")
            print(f"Plan ID: {user.plan_id}")
            print(f"is_admin: {user.is_admin}")
            print(f"is_active: {user.is_active}")
            print("-" * 50)

        print("\n=== Comptage par plan (non-admin, actifs) ===\n")

        # Récupérer tous les plans
        plans = Plan.query.filter_by(is_active=True).all()

        for plan in plans:
            count = User.query.filter_by(
                plan_id=plan.id,
                is_admin=False,
                is_active=True
            ).count()
            print(f"{plan.name}: {count} utilisateur(s)")

        # Sans plan
        no_plan = User.query.filter_by(
            plan_id=None,
            is_admin=False,
            is_active=True
        ).count()
        print(f"Sans plan: {no_plan} utilisateur(s)")

        # Admins
        admins = User.query.filter_by(
            is_admin=True,
            is_active=True
        ).count()
        print(f"Administrateurs: {admins} utilisateur(s)")


if __name__ == '__main__':
    debug_users()
