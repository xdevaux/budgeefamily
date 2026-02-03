#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour mettre à jour les traductions des catégories.
Les catégories actuellement stockées en anglais seront traduites en français.
"""

from app import create_app, db
from app.models import Category

# Dictionnaire de traductions : anglais -> français
TRANSLATIONS = {
    'Home & Garden': 'Maison & Jardin',
    'Electronics & High-tech': 'Électronique & High-tech',
    'Sports & Fitness': 'Sports & Fitness',
    'Education & Training': 'Éducation & Formation',
    'Gaming': 'Jeux vidéo',
    'Travel & Accommodation': 'Voyages & Hébergement',
    'Pets': 'Animaux de compagnie',
    'Video Streaming': 'Streaming vidéo',
    'Other': 'Autres',
    'Beauty & Cosmetics': 'Beauté & Cosmétiques',
    'Food': 'Alimentation',
    'Fuel': 'Carburant',
    'Clothing': 'Vêtements',
    'Restaurant': 'Restaurant',
    'Transportation': 'Transport',
    'Health & Pharmacy': 'Santé & Pharmacie',
    'Leisure & Culture': 'Loisirs & Culture',
    'Audio Streaming': 'Streaming audio',
    'Cloud & Storage': 'Cloud & Stockage',
    'Productivity': 'Productivité',
    'Development': 'Développement',
    'Design & Creative': 'Design & Création',
    'Fitness & Health': 'Fitness & Santé',
    'News & Media': 'Actualités & Médias',
    'Gifts': 'Cadeaux'
}

def update_category_translations():
    """Met à jour les traductions des catégories globales"""
    app = create_app()

    with app.app_context():
        # Récupérer toutes les catégories globales
        categories = Category.query.filter_by(user_id=None).all()

        updated_count = 0

        for category in categories:
            if category.name in TRANSLATIONS:
                # Le nom actuel est en anglais, on le met dans name_en
                category.name_en = category.name
                # On met le nom français
                category.name = TRANSLATIONS[category.name]
                updated_count += 1
                print(f"✓ Catégorie {category.id}: '{category.name_en}' → '{category.name}'")
            else:
                print(f"⚠ Catégorie {category.id}: '{category.name}' - pas de traduction trouvée")

        # Sauvegarder les modifications
        db.session.commit()

        print(f"\n{updated_count} catégorie(s) mise(s) à jour avec succès!")

if __name__ == '__main__':
    update_category_translations()
