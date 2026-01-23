"""
Module de traitement OCR pour les reçus de carte bancaire
"""
import io
import re
import pytesseract
from PIL import Image
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, Optional, Tuple

# Configuration Tesseract
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'  # Chemin par défaut Linux


def preprocess_image(image_data: bytes) -> np.ndarray:
    """
    Prétraite l'image pour améliorer la qualité OCR
    - Gestion des PDFs (conversion première page)
    - Conversion en niveaux de gris
    - Augmentation du contraste
    - Réduction du bruit
    """
    try:
        # Convertir bytes → PIL Image → numpy array
        pil_image = Image.open(io.BytesIO(image_data))

        # Convertir en RGB si nécessaire (pour les images RGBA, CMYK, etc.)
        if pil_image.mode not in ('RGB', 'L'):
            pil_image = pil_image.convert('RGB')

        # Augmenter la résolution si trop petite (améliore l'OCR)
        min_size = 800
        if min(pil_image.size) < min_size:
            ratio = min_size / min(pil_image.size)
            new_size = (int(pil_image.size[0] * ratio), int(pil_image.size[1] * ratio))
            pil_image = pil_image.resize(new_size, Image.LANCZOS)

        # Redimensionner si trop grande
        max_size = 3000
        if max(pil_image.size) > max_size:
            ratio = max_size / max(pil_image.size)
            new_size = (int(pil_image.size[0] * ratio), int(pil_image.size[1] * ratio))
            pil_image = pil_image.resize(new_size, Image.LANCZOS)

        img_array = np.array(pil_image)

        # Convertir en niveaux de gris
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Augmenter le contraste avec CLAHE (égalisation d'histogramme adaptative)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # Débruitage
        gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

        # Binarisation adaptative (améliore la lecture du texte)
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        return binary
    except Exception as e:
        print(f"Erreur prétraitement image: {e}")
        # Fallback: retourner l'image originale convertie en niveaux de gris
        pil_image = Image.open(io.BytesIO(image_data))
        if pil_image.mode not in ('RGB', 'L'):
            pil_image = pil_image.convert('RGB')
        img_array = np.array(pil_image)
        if len(img_array.shape) == 3:
            return cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        return img_array


def extract_text_from_image(image_data: bytes) -> Tuple[str, float]:
    """
    Extrait le texte d'une image de reçu avec OCR
    Retourne (texte_extrait, score_de_confiance)
    """
    try:
        # Prétraiter l'image
        processed_img = preprocess_image(image_data)

        # Essayer plusieurs configurations PSM (Page Segmentation Mode)
        # PSM 3 = Fully automatic page segmentation (meilleur pour documents complets)
        # PSM 6 = Assume a single uniform block of text (bon pour reçus)
        # PSM 11 = Sparse text. Find as much text as possible in no particular order

        configs = [
            r'--oem 3 --psm 6 -l fra',   # Block de texte uniforme (par défaut)
            r'--oem 3 --psm 3 -l fra',   # Segmentation automatique complète
            r'--oem 3 --psm 11 -l fra',  # Texte épars
        ]

        best_text = ""
        best_confidence = 0.0

        for custom_config in configs:
            try:
                # Extraire le texte avec données de confiance
                data = pytesseract.image_to_data(
                    processed_img,
                    config=custom_config,
                    output_type=pytesseract.Output.DICT
                )

                # Calculer le score de confiance moyen
                confidences = [int(conf) for conf in data['conf'] if conf != '-1']
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                # Extraire le texte complet
                text = pytesseract.image_to_string(processed_img, config=custom_config, lang='fra')

                # Garder le meilleur résultat
                if avg_confidence > best_confidence or (avg_confidence > 0 and len(text) > len(best_text)):
                    best_text = text
                    best_confidence = avg_confidence

                # Si on a un bon résultat, ne pas essayer les autres configs
                if best_confidence > 70:
                    break

            except Exception as e:
                print(f"Erreur avec config {custom_config}: {e}")
                continue

        return best_text, best_confidence

    except Exception as e:
        print(f"Erreur lors de l'extraction OCR : {e}")
        import traceback
        traceback.print_exc()
        return "", 0.0


def parse_amount(text: str) -> Optional[float]:
    """
    Cherche et extrait le montant total du reçu
    Patterns recherchés : "TOTAL", "MONTANT", "CARTE", suivi d'un nombre avec €
    """
    # Normaliser le texte
    text_upper = text.upper()

    # Remplacer les erreurs OCR courantes
    text_upper = text_upper.replace('O', '0').replace('o', '0')  # O → 0
    text_upper = text_upper.replace('l', '1').replace('I', '1')  # l/I → 1

    # Patterns pour détecter le montant total (plus permissifs)
    patterns = [
        # Avec mots-clés
        r'TOTAL[:\s]*([0-9]+[,\.\s]?[0-9]*)\s*(?:€|EUR|EUROS?)?',
        r'MONTANT[:\s]*([0-9]+[,\.\s]?[0-9]*)\s*(?:€|EUR|EUROS?)?',
        r'CARTE[:\s]*([0-9]+[,\.\s]?[0-9]*)\s*(?:€|EUR|EUROS?)?',
        r'PAIEMENT[:\s]*([0-9]+[,\.\s]?[0-9]*)\s*(?:€|EUR|EUROS?)?',
        r'A\s*PAYER[:\s]*([0-9]+[,\.\s]?[0-9]*)\s*(?:€|EUR|EUROS?)?',
        r'NET\s*A\s*PAYER[:\s]*([0-9]+[,\.\s]?[0-9]*)\s*(?:€|EUR|EUROS?)?',
        # Montant avec symbole €
        r'([0-9]+[,\.][0-9]{1,2})\s*€',
        r'([0-9]+[,\.][0-9]{1,2})\s*EUR',
        r'€\s*([0-9]+[,\.][0-9]{1,2})',
        r'EUR\s*([0-9]+[,\.][0-9]{1,2})',
        # Montant sans décimales
        r'TOTAL[:\s]*([0-9]+)\s*(?:€|EUR|EUROS?)',
        r'([0-9]+)\s*€',
    ]

    for pattern in patterns:
        match = re.search(pattern, text_upper)
        if match:
            amount_str = match.group(1)
            # Nettoyer la chaîne
            amount_str = amount_str.replace(' ', '').replace(',', '.')
            try:
                amount = float(amount_str)
                if 0 < amount < 100000:  # Montant raisonnable (entre 0 et 100 000€)
                    return amount
            except ValueError:
                continue

    # Si aucun pattern trouvé, chercher tous les montants et prendre le plus gros
    all_amounts = re.findall(r'([0-9]+[,\.][0-9]{1,2})\s*(?:€|EUR)?', text_upper)
    if all_amounts:
        amounts = []
        for a in all_amounts:
            try:
                val = float(a.replace(',', '.').replace(' ', ''))
                if 0 < val < 100000:
                    amounts.append(val)
            except ValueError:
                continue
        if amounts:
            return max(amounts)

    return None


def parse_date(text: str) -> Optional[datetime]:
    """
    Cherche et extrait la date du reçu
    Formats acceptés : DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, etc.
    """
    # Remplacer les erreurs OCR courantes pour les dates
    text = text.replace('O', '0').replace('o', '0')
    text = text.replace('l', '1').replace('I', '1')

    # Patterns de dates (du plus spécifique au plus général)
    date_patterns = [
        # Format complet avec séparateurs
        r'(\d{1,2})[/\-.\s](\d{1,2})[/\-.\s](\d{4})',  # DD/MM/YYYY ou D/M/YYYY
        r'(\d{1,2})[/\-.\s](\d{1,2})[/\-.\s](\d{2})',  # DD/MM/YY
        # Format texte
        r'(\d{1,2})\s+(JAN|FEV|FEB|MAR|AVR|APR|MAI|MAY|JUN|JUI|JUL|AOU|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s+(\d{4})',
        # Format sans séparateur
        r'(\d{2})(\d{2})(\d{4})',  # DDMMYYYY
        r'(\d{2})(\d{2})(\d{2})',  # DDMMYY
    ]

    # Mapping des mois texte
    month_map = {
        'JAN': 1, 'FEV': 2, 'FEB': 2, 'MAR': 3, 'AVR': 4, 'APR': 4,
        'MAI': 5, 'MAY': 5, 'JUN': 6, 'JUI': 7, 'JUL': 7,
        'AOU': 8, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }

    for pattern in date_patterns:
        matches = re.findall(pattern, text.upper())
        for match in matches:
            try:
                if len(match) == 3:
                    day, month, year = match

                    # Si le mois est du texte
                    if month.isalpha():
                        month = str(month_map.get(month[:3], 1))

                    # Nettoyer les espaces
                    day = day.strip()
                    month = month.strip()
                    year = year.strip()

                    # Gérer l'année courte (YY → YYYY)
                    if len(year) == 2:
                        year_int = int(year)
                        if year_int > 50:
                            year = '19' + year
                        else:
                            year = '20' + year

                    # Créer la date
                    date_obj = datetime(int(year), int(month), int(day))

                    # Vérifier que la date est raisonnable (pas dans le futur, pas trop ancienne)
                    now = datetime.now()
                    if date_obj <= now and date_obj >= datetime(now.year - 5, 1, 1):
                        return date_obj
            except (ValueError, AttributeError):
                continue

    return None


def parse_merchant_name(text: str) -> Optional[str]:
    """
    Essaie d'identifier le nom du commerçant
    Généralement en haut du reçu (premières lignes)
    """
    lines = text.split('\n')

    # Prendre les 5 premières lignes non vides
    top_lines = [line.strip() for line in lines[:5] if line.strip()]

    if not top_lines:
        return None

    # Le nom du commerçant est souvent la ligne la plus longue en haut
    merchant_candidates = [line for line in top_lines if len(line) > 3]

    if merchant_candidates:
        # Prendre la ligne la plus longue
        merchant_name = max(merchant_candidates, key=len)
        # Nettoyer et limiter la longueur
        merchant_name = re.sub(r'\s+', ' ', merchant_name).strip()
        return merchant_name[:100]

    return None


def guess_category(merchant_name: str) -> Optional[str]:
    """
    Devine la catégorie d'achat depuis le nom du commerçant
    """
    if not merchant_name:
        return None

    merchant_upper = merchant_name.upper()

    # Mapping commerçants → catégories
    category_keywords = {
        'Alimentation': ['CARREFOUR', 'AUCHAN', 'LECLERC', 'LIDL', 'ALDI', 'INTERMARCHE',
                        'SUPER', 'MARKET', 'EPICERIE', 'BOULANGERIE', 'BOUCHERIE'],
        'Carburant': ['TOTAL', 'BP', 'SHELL', 'ESSO', 'STATION', 'ESSENCE', 'CARBURANT'],
        'Restaurant': ['RESTAURANT', 'CAFE', 'BRASSERIE', 'PIZZERIA', 'BURGER',
                      'MCDONALD', 'KFC', 'QUICK', 'BAR', 'BISTRO'],
        'Transport': ['SNCF', 'RATP', 'UBER', 'TAXI', 'METRO', 'BUS', 'TRAIN'],
        'Santé': ['PHARMACIE', 'HOPITAL', 'CLINIQUE', 'MEDECIN', 'DENTISTE'],
        'Loisirs': ['CINEMA', 'THEATRE', 'SPORT', 'GYM', 'PISCINE', 'CONCERT'],
        'Vêtements': ['ZARA', 'H&M', 'KIABI', 'DECATHLON', 'MODE', 'VETEMENT'],
        'Bricolage': ['LEROY', 'CASTORAMA', 'BRICORAMA', 'BRICO'],
    }

    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in merchant_upper:
                return category

    return 'Autres dépenses'


def process_receipt_ocr(image_data: bytes, debug: bool = False) -> Dict:
    """
    Traite un reçu CB et extrait toutes les informations

    Retourne un dictionnaire avec :
    - merchant_name: Nom du commerçant
    - amount: Montant de l'achat
    - purchase_date: Date de l'achat
    - category_name: Catégorie devinée
    - ocr_confidence: Score de confiance (0-100)
    - raw_text: Texte brut extrait (pour debug)
    """
    # Extraire le texte
    text, confidence = extract_text_from_image(image_data)

    # Mode debug : afficher le texte brut
    if debug:
        print("=" * 80)
        print("TEXTE EXTRAIT PAR OCR:")
        print("-" * 80)
        print(text)
        print("-" * 80)
        print(f"Confiance: {confidence:.1f}%")
        print("=" * 80)

    # Parser les informations
    merchant_name = parse_merchant_name(text)
    amount = parse_amount(text)
    purchase_date = parse_date(text)
    category_name = guess_category(merchant_name) if merchant_name else 'Autres dépenses'

    # Debug : afficher les résultats du parsing
    if debug:
        print(f"Commerçant détecté: {merchant_name or 'AUCUN'}")
        print(f"Montant détecté: {amount or 'AUCUN'}")
        print(f"Date détectée: {purchase_date or 'AUCUNE'}")
        print(f"Catégorie: {category_name}")
        print("=" * 80)

    return {
        'merchant_name': merchant_name or 'Commerçant inconnu',
        'amount': amount or 0.0,
        'purchase_date': purchase_date or datetime.now(),
        'category_name': category_name,
        'ocr_confidence': confidence,
        'raw_text': text  # Utile pour debug
    }
