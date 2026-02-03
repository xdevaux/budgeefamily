#!/usr/bin/env python3
"""
Script pour mettre à jour les descriptions des services par défaut
avec les traductions françaises et anglaises correctes
"""
from app import create_app, db
from app.models import Service

# Dictionnaire des traductions
SERVICE_TRANSLATIONS = {
    "Adobe Creative Cloud": {
        "fr": "Suite créative Adobe (Photoshop, Illustrator, etc.)",
        "en": "Adobe Creative Suite (Photoshop, Illustrator, etc.)"
    },
    "Canal+": {
        "fr": "Chaîne de télévision française premium",
        "en": "French premium television channel"
    },
    "JetBrains": {
        "fr": "Outils de développement professionnels",
        "en": "Professional development tools"
    },
    "Budgee Family": {
        "fr": "Gestionnaire d'abonnements intelligent",
        "en": "Smart subscription manager"
    },
    "Netflix": {
        "fr": "Service de streaming vidéo",
        "en": "Video streaming service"
    },
    "Deezer": {
        "fr": "Service de streaming musical français",
        "en": "French music streaming service"
    },
    "Disney+": {
        "fr": "Service de streaming vidéo Disney, Pixar, Marvel, Star Wars",
        "en": "Disney, Pixar, Marvel, Star Wars video streaming service"
    },
    "Spotify": {
        "fr": "Service de streaming audio et podcasts",
        "en": "Audio and podcast streaming service"
    },
    "Apple Music": {
        "fr": "Service de streaming musical Apple",
        "en": "Apple music streaming service"
    },
    "YouTube Premium": {
        "fr": "YouTube sans publicité avec YouTube Music",
        "en": "Ad-free YouTube with YouTube Music"
    },
    "Amazon Prime Video": {
        "fr": "Service de streaming vidéo Amazon",
        "en": "Amazon video streaming service"
    },
    "OCS": {
        "fr": "Service de streaming cinéma et séries",
        "en": "Movies and series streaming service"
    },
    "Microsoft 365": {
        "fr": "Suite bureautique Microsoft (Office, OneDrive, etc.)",
        "en": "Microsoft office suite (Office, OneDrive, etc.)"
    },
    "Google One": {
        "fr": "Stockage cloud Google étendu",
        "en": "Extended Google cloud storage"
    },
    "iCloud+": {
        "fr": "Stockage cloud Apple avec fonctionnalités premium",
        "en": "Apple cloud storage with premium features"
    }
}

def update_service_descriptions():
    """Met à jour les descriptions des services par défaut"""
    app = create_app()

    with app.app_context():
        updated_count = 0

        # Récupérer tous les services globaux
        all_services = Service.query.filter_by(user_id=None).all()

        for service in all_services:
            if service.name in SERVICE_TRANSLATIONS:
                translations = SERVICE_TRANSLATIONS[service.name]
                service.description = translations["fr"]
                service.description_en = translations["en"]
                updated_count += 1
                print(f"✓ Updated: {service.name}")
                print(f"  FR: {translations['fr']}")
                print(f"  EN: {translations['en']}\n")
            else:
                # Pour les services non définis, garder la description FR et créer une EN
                if service.description and not service.description_en:
                    service.description_en = service.description  # Temporairement identique
                    print(f"⚠ Not in dictionary: {service.name}")
                    print(f"  Kept: {service.description}\n")

        db.session.commit()
        print(f"\n{'='*60}")
        print(f"Total services updated: {updated_count}/{len(all_services)}")
        print(f"{'='*60}")

if __name__ == "__main__":
    update_service_descriptions()
