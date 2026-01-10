#!/usr/bin/env python3
"""
Script pour migrer les logos depuis les fichiers locaux vers la base de données
"""

import os
import base64
import mimetypes
from app import create_app, db
from app.models import Category, Service

def get_logo_data_from_file(file_path):
    """Lit un fichier logo et le convertit en base64"""
    if not os.path.exists(file_path):
        return None, None

    # Lire le fichier
    with open(file_path, 'rb') as f:
        file_data = f.read()

    # Convertir en base64
    base64_data = base64.b64encode(file_data).decode('utf-8')

    # Déterminer le type MIME
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        # Par défaut, PNG
        mime_type = 'image/png'

    return base64_data, mime_type


def migrate_logos():
    app = create_app()

    with app.app_context():
        print("=== Migration des logos vers la base de données ===\n")

        # Répertoire des logos
        logo_dir = '/opt/subly.cloud/app/static/uploads/logos'

        if not os.path.exists(logo_dir):
            print(f"❌ Le répertoire {logo_dir} n'existe pas.")
            return

        # Migrer les logos des catégories
        print("Migration des logos de catégories...")
        categories_migrated = 0
        categories = Category.query.filter(Category.logo_url.isnot(None)).all()

        for category in categories:
            if category.logo_data:
                # Déjà migré
                continue

            # Extraire le nom du fichier depuis logo_url
            if '/static/uploads/logos/' in category.logo_url:
                filename = os.path.basename(category.logo_url)
                file_path = os.path.join(logo_dir, filename)

                logo_data, mime_type = get_logo_data_from_file(file_path)

                if logo_data:
                    category.logo_data = logo_data
                    category.logo_mime_type = mime_type
                    categories_migrated += 1
                    print(f"  ✓ Catégorie '{category.name}' - Logo migré ({mime_type})")
                else:
                    print(f"  ⚠ Catégorie '{category.name}' - Fichier {filename} introuvable")

        # Migrer les logos des services
        print("\nMigration des logos de services...")
        services_migrated = 0
        services = Service.query.filter(Service.logo_url.isnot(None)).all()

        for service in services:
            if service.logo_data:
                # Déjà migré
                continue

            # Extraire le nom du fichier depuis logo_url
            if '/static/uploads/logos/' in service.logo_url:
                filename = os.path.basename(service.logo_url)
                file_path = os.path.join(logo_dir, filename)

                logo_data, mime_type = get_logo_data_from_file(file_path)

                if logo_data:
                    service.logo_data = logo_data
                    service.logo_mime_type = mime_type
                    services_migrated += 1
                    print(f"  ✓ Service '{service.name}' - Logo migré ({mime_type})")
                else:
                    print(f"  ⚠ Service '{service.name}' - Fichier {filename} introuvable")

        # Sauvegarder les modifications
        db.session.commit()

        print(f"\n✅ Migration terminée !")
        print(f"   - Catégories migrées: {categories_migrated}")
        print(f"   - Services migrés: {services_migrated}")
        print(f"\nLes logos sont maintenant stockés en base de données.")
        print("Les fichiers dans /static/uploads/logos/ peuvent être supprimés.")


if __name__ == '__main__':
    migrate_logos()
