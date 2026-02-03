"""Script pour ajouter les descriptions en anglais aux types de crédits par défaut"""

from app import create_app, db
from app.models import CreditType

def update_credit_type_descriptions():
    """Met à jour les descriptions en anglais des types de crédits par défaut"""

    # Dictionnaire des traductions : {nom_fr: description_en}
    translations = {
        'Prêt immobilier': 'Credit for purchasing real estate',
        'Prêt auto': 'Credit for purchasing a vehicle',
        'Prêt personnel': 'Consumer credit',
        'Prêt étudiant': 'Credit to finance studies',
        'Crédit travaux': 'Credit for renovation work'
    }

    app = create_app()
    with app.app_context():
        # Récupérer tous les types de crédits globaux (par défaut)
        global_types = CreditType.query.filter_by(user_id=None).all()

        updated_count = 0
        for credit_type in global_types:
            if credit_type.name in translations:
                credit_type.description_en = translations[credit_type.name]
                updated_count += 1
                print(f"✓ Mis à jour: {credit_type.name} -> {credit_type.description_en}")

        # Sauvegarder les modifications
        db.session.commit()
        print(f"\n✓ {updated_count} type(s) de crédit mis à jour avec succès!")

if __name__ == '__main__':
    update_credit_type_descriptions()
