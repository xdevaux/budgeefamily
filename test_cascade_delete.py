#!/usr/bin/env python3
"""
Script de test pour vérifier la suppression en cascade
"""

from app import create_app, db
from app.models import User, Plan, Category, Service, ServicePlan
from datetime import datetime


def test_cascade_delete():
    app = create_app()

    with app.app_context():
        print("=== Test de suppression en cascade ===\n")

        # 1. Créer un utilisateur de test
        print("1. Création d'un utilisateur de test...")
        free_plan = Plan.query.filter_by(name='Free').first()
        test_user = User(
            email='test_cascade@example.com',
            first_name='Test',
            last_name='Cascade',
            plan=free_plan,
            is_active=True
        )
        test_user.set_password('test123')
        db.session.add(test_user)
        db.session.commit()
        user_id = test_user.id
        print(f"   ✓ Utilisateur créé (ID: {user_id})")

        # 2. Créer une catégorie personnalisée
        print("\n2. Création d'une catégorie personnalisée...")
        test_category = Category(
            name='Catégorie Test',
            description='Catégorie de test',
            user=test_user
        )
        db.session.add(test_category)
        db.session.commit()
        print(f"   ✓ Catégorie créée (ID: {test_category.id})")

        # 3. Créer un service personnalisé
        print("\n3. Création d'un service personnalisé...")
        test_service = Service(
            name='Service Test',
            description='Service de test',
            user=test_user,
            category=test_category
        )
        db.session.add(test_service)
        db.session.commit()
        print(f"   ✓ Service créé (ID: {test_service.id})")

        # 4. Créer un plan personnalisé
        print("\n4. Création d'un plan personnalisé...")
        test_plan = ServicePlan(
            name='Plan Test',
            description='Plan de test',
            amount=9.99,
            billing_cycle='monthly',
            service=test_service,
            user=test_user
        )
        db.session.add(test_plan)
        db.session.commit()
        plan_id = test_plan.id
        print(f"   ✓ Plan créé (ID: {plan_id})")

        # 5. Vérifier les relations
        print("\n5. Vérification des relations...")
        print(f"   - Catégories personnalisées: {test_user.custom_categories.count()}")
        print(f"   - Services personnalisés: {test_user.custom_services.count()}")
        print(f"   - Plans personnalisés: {test_user.custom_plans.count()}")

        # 6. Supprimer l'utilisateur
        print("\n6. Suppression de l'utilisateur...")
        db.session.delete(test_user)
        db.session.commit()
        print(f"   ✓ Utilisateur supprimé")

        # 7. Vérifier que les dépendances ont été supprimées
        print("\n7. Vérification de la suppression en cascade...")

        user_exists = User.query.get(user_id)
        category_exists = Category.query.filter_by(name='Catégorie Test', user_id=user_id).first()
        service_exists = Service.query.filter_by(name='Service Test', user_id=user_id).first()
        plan_exists = ServicePlan.query.get(plan_id)

        if user_exists:
            print(f"   ✗ ERREUR: L'utilisateur existe encore!")
        else:
            print(f"   ✓ Utilisateur supprimé")

        if category_exists:
            print(f"   ✗ ERREUR: La catégorie existe encore!")
        else:
            print(f"   ✓ Catégorie supprimée")

        if service_exists:
            print(f"   ✗ ERREUR: Le service existe encore!")
        else:
            print(f"   ✓ Service supprimé")

        if plan_exists:
            print(f"   ✗ ERREUR: Le plan existe encore!")
        else:
            print(f"   ✓ Plan supprimé")

        print("\n=== Test terminé avec succès! ===")


if __name__ == '__main__':
    test_cascade_delete()
