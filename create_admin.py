#!/usr/bin/env python3
"""
Script pour créer un utilisateur administrateur
"""

from app import create_app, db
from app.models import User, Plan
import getpass


def create_admin_user():
    app = create_app()

    with app.app_context():
        print("=== Création d'un utilisateur administrateur ===\n")

        email = input("Email : ")

        # Vérifier si l'utilisateur existe déjà
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"\n❌ Un utilisateur avec l'email {email} existe déjà.")
            return

        first_name = input("Prénom : ")
        last_name = input("Nom : ")
        password = getpass.getpass("Mot de passe : ")
        password_confirm = getpass.getpass("Confirmer le mot de passe : ")

        if password != password_confirm:
            print("\n❌ Les mots de passe ne correspondent pas.")
            return

        # Demander le plan
        print("\nPlan :")
        print("1. Free (gratuit)")
        print("2. Premium")
        plan_choice = input("Choisir (1 ou 2) : ")

        if plan_choice == "2":
            plan = Plan.query.filter_by(name='Premium').first()
        else:
            plan = Plan.query.filter_by(name='Free').first()

        if not plan:
            print("\n❌ Erreur : Les plans n'existent pas. Exécutez d'abord init_db.py")
            return

        # Créer l'utilisateur
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            plan=plan,
            is_active=True
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        print(f"\n✅ Utilisateur créé avec succès !")
        print(f"   Email : {email}")
        print(f"   Nom : {first_name} {last_name}")
        print(f"   Plan : {plan.name}")
        print(f"\nVous pouvez maintenant vous connecter avec cet email et mot de passe.")


if __name__ == '__main__':
    create_admin_user()
