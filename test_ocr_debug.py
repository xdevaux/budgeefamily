#!/usr/bin/env python3
"""
Script de test OCR avec mode debug pour analyser vos reçus
Usage: python test_ocr_debug.py <chemin_vers_image_ou_pdf>
"""
import sys
import os

def test_receipt(file_path):
    """Teste l'OCR sur un fichier de reçu"""

    if not os.path.exists(file_path):
        print(f"❌ Fichier non trouvé: {file_path}")
        return False

    print(f"📄 Analyse du fichier: {file_path}")
    print("=" * 80)

    # Lire le fichier
    with open(file_path, 'rb') as f:
        image_data = f.read()

    print(f"✓ Fichier chargé ({len(image_data)} bytes)")

    # Importer le module OCR
    try:
        from app.utils.ocr_processor import process_receipt_ocr
    except ImportError:
        # Si on n'est pas dans le bon répertoire
        sys.path.insert(0, '/opt/budgeefamily')
        from app.utils.ocr_processor import process_receipt_ocr

    # Traiter avec le mode debug activé
    print("\n🔍 Traitement OCR en cours...\n")
    result = process_receipt_ocr(image_data, debug=True)

    # Afficher les résultats
    print("\n📊 RÉSULTATS FINAUX:")
    print("=" * 80)
    print(f"Commerçant : {result['merchant_name']}")
    print(f"Montant    : {result['amount']} €")
    print(f"Date       : {result['purchase_date'].strftime('%d/%m/%Y %H:%M')}")
    print(f"Catégorie  : {result['category_name']}")
    print(f"Confiance  : {result['ocr_confidence']:.1f}%")
    print("=" * 80)

    # Diagnostic
    print("\n🔍 DIAGNOSTIC:")
    if result['amount'] == 0.0:
        print("⚠️  MONTANT NON DÉTECTÉ")
        print("   → Vérifiez que le montant total est visible sur le reçu")
        print("   → Cherchez les mots: TOTAL, MONTANT, A PAYER, NET A PAYER")
        print("   → Le symbole € doit être présent")

    if result['merchant_name'] == 'Commerçant inconnu':
        print("⚠️  COMMERÇANT NON DÉTECTÉ")
        print("   → Le nom du commerçant devrait être en haut du reçu")
        print("   → Vérifiez que le texte en haut est lisible")

    if result['purchase_date'].date() == __import__('datetime').datetime.now().date():
        print("⚠️  DATE NON DÉTECTÉE (date du jour utilisée)")
        print("   → Vérifiez qu'une date au format JJ/MM/AAAA est présente")
        print("   → Formats acceptés: 23/01/2024, 23-01-2024, 23.01.2024")

    if result['ocr_confidence'] < 50:
        print("⚠️  CONFIANCE OCR FAIBLE")
        print("   → Essayez avec une image de meilleure qualité")
        print("   → Augmentez la luminosité de la photo")
        print("   → Évitez les ombres et reflets")

    print("\n💡 CONSEILS:")
    print("   - Prenez des photos bien éclairées et nettes")
    print("   - Scannez plutôt que photographiez si possible")
    print("   - Assurez-vous que tout le texte est visible")
    print("   - Le reçu doit être à plat (pas de plis)")

    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_ocr_debug.py <chemin_vers_image_ou_pdf>")
        print("\nExemple:")
        print("  python test_ocr_debug.py /chemin/vers/recu.jpg")
        print("  python test_ocr_debug.py /chemin/vers/recu.pdf")
        sys.exit(1)

    file_path = sys.argv[1]
    success = test_receipt(file_path)
    sys.exit(0 if success else 1)
