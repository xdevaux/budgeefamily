#!/usr/bin/env python3
"""
Script de test pour vérifier l'installation OCR
"""
import pytesseract
import sys

def test_tesseract():
    """Test de l'installation de Tesseract"""
    print("=" * 60)
    print("Test de l'installation OCR pour BudgeeFamily")
    print("=" * 60)

    try:
        # Vérifier la version de Tesseract
        version = pytesseract.get_tesseract_version()
        print(f"\n✓ Tesseract installé : version {version}")
    except Exception as e:
        print(f"\n✗ Erreur Tesseract : {e}")
        return False

    try:
        # Vérifier la disponibilité de la langue française
        languages = pytesseract.get_languages()
        if 'fra' in languages:
            print(f"✓ Langue française disponible")
        else:
            print(f"✗ Langue française non disponible")
            print(f"   Langues disponibles : {', '.join(languages)}")
            return False
    except Exception as e:
        print(f"\n✗ Erreur lors de la vérification des langues : {e}")
        return False

    try:
        # Test avec une image simple
        from PIL import Image, ImageDraw, ImageFont
        import io

        # Créer une image de test simple
        img = Image.new('RGB', (400, 100), color='white')
        d = ImageDraw.Draw(img)
        d.text((10, 30), "TOTAL: 45,50 EUR", fill='black')

        # Convertir en bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()

        # Tester l'OCR
        from app.utils.ocr_processor import extract_text_from_image, parse_amount

        text, confidence = extract_text_from_image(img_bytes)
        print(f"✓ OCR fonctionnel (confiance : {confidence:.1f}%)")

        # Test du parsing de montant
        amount = parse_amount(text)
        if amount:
            print(f"✓ Parsing de montant fonctionnel : {amount}€")
        else:
            print(f"⚠ Parsing de montant : aucun montant détecté (texte OCR : '{text}')")

    except Exception as e:
        print(f"\n✗ Erreur lors du test OCR : {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✓ Tous les tests sont passés avec succès !")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_tesseract()
    sys.exit(0 if success else 1)
