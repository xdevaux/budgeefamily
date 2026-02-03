#!/usr/bin/env python3
"""
Script pour mettre à jour les descriptions des catégories par défaut
avec les traductions françaises et anglaises correctes
"""
from app import create_app, db
from app.models import Category

# Dictionnaire des traductions
CATEGORY_TRANSLATIONS = {
    "Beauty & Cosmetics": {
        "fr": "Coiffeur, esthétique, cosmétiques",
        "en": "Hairdresser, aesthetics, cosmetics"
    },
    "Other": {
        "fr": "Dépenses diverses non catégorisées",
        "en": "Other types of subscriptions"
    },
    "Food": {
        "fr": "Courses alimentaires, supermarché",
        "en": "Grocery shopping, supermarket"
    },
    "Fuel": {
        "fr": "Essence, diesel, station-service",
        "en": "Gasoline, diesel, gas station"
    },
    "Clothing": {
        "fr": "Vêtements, chaussures, accessoires",
        "en": "Clothes, shoes, accessories"
    },
    "Restaurant": {
        "fr": "Restaurants, fast-food, livraison",
        "en": "Restaurants, fast-food, delivery"
    },
    "Transportation": {
        "fr": "Transports en commun, taxi, parking",
        "en": "Public transport, taxi, parking"
    },
    "Health & Pharmacy": {
        "fr": "Médicaments, pharmacie, soins",
        "en": "Medicines, pharmacy, healthcare"
    },
    "Leisure & Culture": {
        "fr": "Cinéma, concerts, musées, spectacles",
        "en": "Cinema, concerts, museums, shows"
    },
    "Home & Garden": {
        "fr": "Bricolage, jardinage, décoration",
        "en": "DIY, gardening, decoration"
    },
    "Electronics & High-tech": {
        "fr": "Informatique, électronique, gadgets",
        "en": "Computing, electronics, gadgets"
    },
    "Sports & Fitness": {
        "fr": "Équipement sportif, salle de sport",
        "en": "Sports equipment, gym"
    },
    "Education & Training": {
        "fr": "Livres, formations, cours",
        "en": "Books, training, courses"
    },
    "Gaming": {
        "fr": "Services de jeux et gaming",
        "en": "Gaming and game services"
    },
    "Travel & Accommodation": {
        "fr": "Hôtels, voyages, locations",
        "en": "Hotels, travel, rentals"
    },
    "Pets": {
        "fr": "Nourriture et soins pour animaux",
        "en": "Pet food and care"
    },
    "Video Streaming": {
        "fr": "Services de streaming vidéo et films",
        "en": "Video streaming and movies services"
    },
    "Audio Streaming": {
        "fr": "Services de musique et podcasts",
        "en": "Music and podcast services"
    },
    "Cloud & Storage": {
        "fr": "Services de stockage en ligne",
        "en": "Cloud storage services"
    },
    "Productivity": {
        "fr": "Outils de productivité et bureautique",
        "en": "Productivity and office tools"
    },
    "Development": {
        "fr": "Outils pour développeurs",
        "en": "Developer tools"
    },
    "Design & Creative": {
        "fr": "Outils de design et création",
        "en": "Design and creative tools"
    },
    "Fitness & Health": {
        "fr": "Applications de fitness et santé",
        "en": "Fitness and health apps"
    },
    "News & Media": {
        "fr": "Abonnements à des journaux et médias",
        "en": "News and media subscriptions"
    },
    "Gifts": {
        "fr": "Cadeaux pour occasions spéciales",
        "en": "Gifts for special occasions"
    }
}

def update_category_descriptions():
    """Met à jour les descriptions des catégories par défaut"""
    app = create_app()

    with app.app_context():
        updated_count = 0

        for category_name, translations in CATEGORY_TRANSLATIONS.items():
            category = Category.query.filter_by(user_id=None, name=category_name).first()

            if category:
                category.description = translations["fr"]
                category.description_en = translations["en"]
                updated_count += 1
                print(f"✓ Updated: {category_name}")
                print(f"  FR: {translations['fr']}")
                print(f"  EN: {translations['en']}\n")
            else:
                print(f"✗ Not found: {category_name}\n")

        db.session.commit()
        print(f"\n{'='*60}")
        print(f"Total categories updated: {updated_count}/{len(CATEGORY_TRANSLATIONS)}")
        print(f"{'='*60}")

if __name__ == "__main__":
    update_category_descriptions()
