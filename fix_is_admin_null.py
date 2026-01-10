#!/usr/bin/env python3
"""
Script pour corriger les valeurs NULL dans is_admin
"""

from app import create_app, db
from app.models import User


def fix_is_admin_null():
    app = create_app()

    with app.app_context():
        print("=== Correction des valeurs NULL dans is_admin ===\n")

        # Récupérer tous les utilisateurs avec is_admin = NULL
        users_with_null = User.query.filter(User.is_admin == None).all()

        print(f"Nombre d'utilisateurs avec is_admin = NULL : {len(users_with_null)}\n")

        if len(users_with_null) == 0:
            print("Aucune correction nécessaire.")
            return

        for user in users_with_null:
            print(f"Correction de l'utilisateur : {user.email}")
            user.is_admin = False

        db.session.commit()

        print(f"\n✅ {len(users_with_null)} utilisateur(s) corrigé(s) avec succès !")


if __name__ == '__main__':
    fix_is_admin_null()
