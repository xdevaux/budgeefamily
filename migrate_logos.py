#!/usr/bin/env python3
"""
Script de migration pour ajouter les logos aux services Netflix, Spotify et Prime Video
"""

from app import create_app, db
from app.models import Service

def migrate_logos():
    app = create_app()

    with app.app_context():
        print("Mise à jour des logos des services...")

        # Définir les logos à ajouter
        services_logos = {
            'Netflix': '/static/uploads/logos/netflix.png',
            'Spotify': '/static/uploads/logos/spotify.png',
            'Prime Video': '/static/uploads/logos/primevideo.png',
            'Apple Music': '/static/uploads/logos/applemusic.png',
            'Microsoft 365': '/static/uploads/logos/microsoft365.png',
            'JetBrains': '/static/uploads/logos/jetbrains.png',
            'Adobe Creative Cloud': '/static/uploads/logos/adobe.png',
            'Blizzard': '/static/uploads/logos/blizzard.png',
            'Canal+': '/static/uploads/logos/canalplus.png',
            'Deezer': '/static/uploads/logos/deezer.png',
            'Disney+': '/static/uploads/logos/disneyplus.png',
            'Dropbox': '/static/uploads/logos/dropbox.png',
            'YouTube Premium': '/static/uploads/logos/youtubepremium.png'
        }

        updated_count = 0

        for service_name, logo_url in services_logos.items():
            # Chercher le service (global uniquement, user_id=None)
            service = Service.query.filter_by(name=service_name, user_id=None).first()

            if service:
                service.logo_url = logo_url
                updated_count += 1
                print(f"✓ Logo ajouté pour {service_name}: {logo_url}")
            else:
                print(f"⚠ Service '{service_name}' non trouvé dans la base de données")

        if updated_count > 0:
            db.session.commit()
            print(f"\n✅ Migration terminée ! {updated_count} service(s) mis à jour.")
        else:
            print("\n⚠ Aucun service n'a été mis à jour.")


if __name__ == '__main__':
    migrate_logos()
