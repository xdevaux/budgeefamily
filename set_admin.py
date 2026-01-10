#!/usr/bin/env python3
"""
Script pour mettre à jour un utilisateur comme administrateur avec le plan Premium
"""

from app import create_app, db
from app.models import User, Plan


def set_user_as_admin():
    app = create_app()

    with app.app_context():
        print("=== Mise à jour de l'utilisateur comme administrateur ===\n")

        # Récupérer l'utilisateur
        user = User.query.filter_by(email='contact@subly.cloud').first()

        if not user:
            print(f"❌ Aucun utilisateur trouvé avec l'email contact@subly.cloud")
            return

        # Récupérer le plan Premium
        premium_plan = Plan.query.filter_by(name='Premium').first()

        if not premium_plan:
            print("❌ Erreur : Le plan Premium n'existe pas.")
            return

        # Mettre à jour l'utilisateur
        user.is_admin = True
        user.plan = premium_plan
        user.is_active = True

        db.session.commit()

        print(f"✅ Utilisateur mis à jour avec succès !")
        print(f"   Email : {user.email}")
        print(f"   Nom : {user.first_name} {user.last_name}")
        print(f"   Administrateur : {user.is_admin}")
        print(f"   Plan : {user.plan.name}")


if __name__ == '__main__':
    set_user_as_admin()
