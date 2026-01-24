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
from pdf2image import convert_from_bytes

# Configuration Tesseract
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'  # Chemin par défaut Linux


def detect_and_correct_skew(gray: np.ndarray) -> np.ndarray:
    """
    Détecte et corrige l'inclinaison de l'image
    """
    try:
        # Binarisation Otsu pour détecter les contours
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Trouver les coordonnées de tous les pixels non-nuls
        coords = np.column_stack(np.where(thresh > 0))

        # Calculer l'angle de rotation avec minAreaRect
        if len(coords) > 0:
            angle = cv2.minAreaRect(coords)[-1]

            # Corriger l'angle (OpenCV retourne un angle entre -90 et 0)
            if angle < -45:
                angle = 90 + angle
            elif angle > 45:
                angle = angle - 90

            # Ne corriger que si l'angle est significatif (> 0.5 degrés)
            if abs(angle) > 0.5:
                print(f"Correction de l'inclinaison: {angle:.2f}°")
                (h, w) = gray.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(gray, M, (w, h),
                                        flags=cv2.INTER_CUBIC,
                                        borderMode=cv2.BORDER_REPLICATE)
                return rotated
    except Exception as e:
        print(f"Erreur correction inclinaison: {e}")

    return gray


def preprocess_image_multi(image_data: bytes) -> list:
    """
    Génère plusieurs versions prétraitées de l'image
    pour tester différentes approches de binarisation
    """
    try:
        # Détecter si c'est un PDF et le convertir en image
        if image_data[:4] == b'%PDF':
            import logging
            logger = logging.getLogger(__name__)
            logger.info("PDF détecté, conversion en cours...")
            print("PDF détecté, conversion en cours...")

            try:
                images = convert_from_bytes(image_data, first_page=1, last_page=1, dpi=400)
                if images:
                    pil_image = images[0]
                    logger.info(f"PDF converti avec succès: {pil_image.size}")
                    print(f"PDF converti: {pil_image.size}")
                else:
                    error_msg = "La conversion PDF n'a retourné aucune image"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            except Exception as pdf_error:
                logger.error(f"Erreur lors de la conversion PDF: {type(pdf_error).__name__}: {pdf_error}")
                import traceback
                logger.error(traceback.format_exc())
                raise
        else:
            pil_image = Image.open(io.BytesIO(image_data))

        # Convertir en RGB si nécessaire
        if pil_image.mode not in ('RGB', 'L'):
            pil_image = pil_image.convert('RGB')

        # Redimensionner intelligemment
        min_size = 1500
        if min(pil_image.size) < min_size:
            ratio = min_size / min(pil_image.size)
            new_size = (int(pil_image.size[0] * ratio), int(pil_image.size[1] * ratio))
            pil_image = pil_image.resize(new_size, Image.LANCZOS)
            print(f"Image agrandie: {new_size}")

        max_size = 4000
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

        # Corriger l'inclinaison
        gray = detect_and_correct_skew(gray)

        # Normalisation de base
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)

        # Débruitage
        gray = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

        processed_versions = []

        # VERSION 1: Binarisation Otsu agressive
        clahe1 = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
        enhanced1 = clahe1.apply(gray)
        _, binary1 = cv2.threshold(enhanced1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_versions.append(('Otsu', binary1))

        # VERSION 2: Binarisation adaptative Gaussian
        clahe2 = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced2 = clahe2.apply(gray)
        binary2 = cv2.adaptiveThreshold(enhanced2, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10)
        processed_versions.append(('Gaussian', binary2))

        # VERSION 3: Binarisation adaptative Mean
        binary3 = cv2.adaptiveThreshold(enhanced2, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 21, 10)
        processed_versions.append(('Mean', binary3))

        # VERSION 4: Approche agressive pour tickets très pâles
        # Augmentation gamma très forte
        gamma = 0.4  # Assombrir l'image
        lookUpTable = np.empty((1, 256), np.uint8)
        for i in range(256):
            lookUpTable[0, i] = np.clip(pow(i / 255.0, gamma) * 255.0, 0, 255)
        dark = cv2.LUT(gray, lookUpTable)

        # CLAHE très agressif
        clahe4 = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(4, 4))
        enhanced4 = clahe4.apply(dark)

        # Binarisation Otsu
        _, binary4 = cv2.threshold(enhanced4, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_versions.append(('Aggressive', binary4))

        # VERSION 5: Approche douce avec seuil manuel
        clahe5 = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(16, 16))
        enhanced5 = clahe5.apply(gray)
        _, binary5 = cv2.threshold(enhanced5, 127, 255, cv2.THRESH_BINARY)
        processed_versions.append(('Manual', binary5))

        return processed_versions

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur prétraitement image: {type(e).__name__}: {e}")
        print(f"Erreur prétraitement image: {e}")
        import traceback
        logger.error(traceback.format_exc())
        traceback.print_exc()

        # Fallback - essayer de charger l'image sans prétraitement
        try:
            # Si c'est un PDF, essayer de le convertir même en mode fallback
            if image_data[:4] == b'%PDF':
                logger.info("Fallback: tentative de conversion PDF simplifiée")
                images = convert_from_bytes(image_data, first_page=1, last_page=1, dpi=200)
                if images:
                    pil_image = images[0]
                else:
                    raise ValueError("Échec conversion PDF en mode fallback")
            else:
                pil_image = Image.open(io.BytesIO(image_data))

            if pil_image.mode not in ('RGB', 'L'):
                pil_image = pil_image.convert('RGB')
            img_array = np.array(pil_image)
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            logger.info("Fallback réussi")
            return [('Fallback', gray)]
        except Exception as fallback_error:
            logger.error(f"Échec du fallback: {fallback_error}")
            raise RuntimeError(f"Impossible de traiter l'image/PDF: {fallback_error}") from e


def preprocess_image(image_data: bytes) -> np.ndarray:
    """
    Prétraite l'image pour améliorer la qualité OCR
    - Gestion des PDFs (conversion première page)
    - Conversion en niveaux de gris
    - Correction de l'inclinaison
    - Augmentation agressive du contraste pour tickets pâles
    - Réduction du bruit
    - Binarisation optimisée
    """
    try:
        # Détecter si c'est un PDF et le convertir en image
        if image_data[:4] == b'%PDF':
            print("PDF détecté, conversion en cours...")
            # Convertir avec une résolution plus élevée pour les tickets de mauvaise qualité
            images = convert_from_bytes(image_data, first_page=1, last_page=1, dpi=400)
            if images:
                pil_image = images[0]
                print(f"PDF converti: {pil_image.size}")
            else:
                raise ValueError("Impossible de convertir le PDF en image")
        else:
            # Convertir bytes → PIL Image
            pil_image = Image.open(io.BytesIO(image_data))

        # Convertir en RGB si nécessaire
        if pil_image.mode not in ('RGB', 'L'):
            pil_image = pil_image.convert('RGB')

        # Augmenter la résolution si trop petite (crucial pour OCR)
        min_size = 1200  # Augmenté de 800 à 1200
        if min(pil_image.size) < min_size:
            ratio = min_size / min(pil_image.size)
            new_size = (int(pil_image.size[0] * ratio), int(pil_image.size[1] * ratio))
            pil_image = pil_image.resize(new_size, Image.LANCZOS)
            print(f"Image agrandie: {new_size}")

        # Redimensionner si trop grande
        max_size = 3500
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

        # Corriger l'inclinaison
        gray = detect_and_correct_skew(gray)

        # Augmentation AGRESSIVE du contraste (crucial pour tickets pâles)
        # 1. Normalisation de l'histogramme
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)

        # 2. CLAHE avec paramètres plus agressifs pour tickets pâles
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
        gray = clahe.apply(gray)

        # 3. Augmentation gamma pour éclaircir les zones sombres
        gamma = 1.2
        lookUpTable = np.empty((1, 256), np.uint8)
        for i in range(256):
            lookUpTable[0, i] = np.clip(pow(i / 255.0, gamma) * 255.0, 0, 255)
        gray = cv2.LUT(gray, lookUpTable)

        # Débruitage (paramètres ajustés)
        gray = cv2.fastNlMeansDenoising(gray, None, h=15, templateWindowSize=7, searchWindowSize=21)

        # Essayer plusieurs méthodes de binarisation et garder la meilleure
        binaries = []

        # Méthode 1: Binarisation adaptative Gaussian
        binary1 = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
        )
        binaries.append(binary1)

        # Méthode 2: Binarisation adaptative Mean
        binary2 = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 8
        )
        binaries.append(binary2)

        # Méthode 3: Otsu
        _, binary3 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        binaries.append(binary3)

        # Retourner la binarisation adaptative Gaussian (généralement la meilleure pour tickets)
        return binaries[0]

    except Exception as e:
        print(f"Erreur prétraitement image: {e}")
        import traceback
        traceback.print_exc()
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
    Teste plusieurs prétraitements et configurations pour trouver le meilleur résultat
    Retourne (texte_extrait, score_de_confiance)
    """
    try:
        # Obtenir plusieurs versions prétraitées
        preprocessed_versions = preprocess_image_multi(image_data)

        # Configurations PSM à tester
        configs = [
            r'--oem 3 --psm 4 -l fra',   # Colonne unique (MEILLEUR pour tickets)
            r'--oem 3 --psm 6 -l fra',   # Block de texte uniforme
            r'--oem 1 --psm 6 -l fra',   # LSTM uniquement
        ]

        best_text = ""
        best_confidence = 0.0
        best_combo = ""

        # Tester chaque combinaison de prétraitement + config
        for preprocess_name, processed_img in preprocessed_versions:
            for custom_config in configs:
                try:
                    # Extraire le texte avec données de confiance
                    data = pytesseract.image_to_data(
                        processed_img,
                        config=custom_config,
                        output_type=pytesseract.Output.DICT
                    )

                    # Calculer le score de confiance moyen
                    confidences = [int(conf) for conf in data['conf'] if conf != '-1' and int(conf) > 0]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                    # Extraire le texte complet
                    text = pytesseract.image_to_string(processed_img, config=custom_config, lang='fra')

                    # Critère de sélection: priorité au texte le plus long si confiance > 30%
                    # Sinon prendre la meilleure confiance
                    is_better = False
                    if avg_confidence > 30:
                        # Si confiance acceptable, préférer le texte le plus long
                        if len(text) > len(best_text) and avg_confidence > best_confidence * 0.8:
                            is_better = True
                    else:
                        # Sinon prendre la meilleure confiance
                        if avg_confidence > best_confidence:
                            is_better = True

                    if is_better:
                        best_text = text
                        best_confidence = avg_confidence
                        best_combo = f"{preprocess_name} + {custom_config}"
                        print(f"Meilleur: {best_combo} - confiance={avg_confidence:.1f}%, longueur={len(text)}")

                except Exception as e:
                    print(f"Erreur avec {preprocess_name} + {custom_config}: {e}")
                    continue

        print(f"Résultat final: {best_combo}")
        return best_text, best_confidence

    except Exception as e:
        print(f"Erreur lors de l'extraction OCR : {e}")
        import traceback
        traceback.print_exc()
        return "", 0.0


def parse_amount(text: str) -> Optional[float]:
    """
    Cherche et extrait le montant total du reçu
    Patterns recherchés : "TOTAL", "MONTANT", "MONTANT REEL", "CARTE", suivi d'un nombre avec €
    """
    # Normaliser le texte
    text_upper = text.upper()

    # Remplacer les erreurs OCR courantes (SAUF S qui sera géré spécifiquement)
    text_upper = text_upper.replace('O', '0').replace('o', '0').replace('Ô', '0')
    text_upper = text_upper.replace('l', '1').replace('I', '1').replace('|', '1')
    # NE PAS remplacer S globalement - sera géré dans les normalisations spécifiques
    text_upper = text_upper.replace('B', '8').replace('b', '8')

    # Chercher spécifiquement "MONTANT REEL" ou "MONTANT" (Intermarché)
    # Pattern très flexible pour "MONTANT REEL"
    montant_reel_patterns = [
        r'M[O0Q]NTANT\s+R[EI3]EL[:\s\.\-]+([0-9]+[,\.\s:]?[0-9]+)\s*(?:€|EUR)',
        r'M[O0Q]NTANT\s+R[EI3]EL[:\s\.\-]+([0-9]+[,\.][0-9]{2})',
        r'M[O0Q]NTANT[:\s]+R[EI3][EI3]L[:\s]+([0-9]+[,\.][0-9]{2})',
    ]

    for pattern in montant_reel_patterns:
        matches = re.findall(pattern, text_upper)
        for match in matches:
            amount_str = match if isinstance(match, str) else match[0]
            amount_str = amount_str.replace(' ', '').replace(',', '.').replace(':', '.')
            try:
                amount = float(amount_str)
                if 0.01 < amount < 10000:
                    print(f"Montant trouvé avec 'MONTANT REEL': {amount}€")
                    return amount
            except ValueError:
                continue

    # Chercher une ligne contenant "MONTANT REEL" et extraire le montant sur la même ligne ou ligne suivante
    lines = text_upper.split('\n')
    for i, line in enumerate(lines):
        if 'M' in line and 'NT' in line and 'R' in line and 'EL' in line:  # MONTANT...REEL
            # Chercher un montant dans cette ligne (avec variations OCR)
            # IMPORTANT: Faire les remplacements dans le bon ordre
            # 1. D'abord remplacer O → 0
            line_normalized = line.replace('O', '0').replace('o', '0')
            # 2. Ensuite remplacer "S0" → "60" AVANT de remplacer tous les S
            line_normalized = re.sub(r'S\s*0[\-/:,\.]', '60.', line_normalized)  # S0- → 60.
            line_normalized = line_normalized.replace('S0', '60').replace('s0', '60')  # S0 → 60
            # 3. Maintenant remplacer les S restants par 6
            line_normalized = line_normalized.replace('S', '6').replace('s', '6')
            line_normalized = line_normalized.replace('d', '0').replace('D', '0')


            amounts_in_line = re.findall(r'([0-9]{1,4}[,\.\-/:][0-9]{2})', line_normalized)
            if amounts_in_line:
                for amt_str in amounts_in_line:
                    try:
                        # Nettoyer tous les séparateurs possibles
                        amount = float(amt_str.replace(',', '.').replace('-', '.').replace('/', '.').replace(':', '.'))
                        if 0.01 < amount < 10000:
                            print(f"Montant trouvé sur ligne MONTANT REEL: {amount}€")
                            return amount
                    except ValueError:
                        continue

            # Chercher sur la ligne suivante
            if i + 1 < len(lines):
                line_next = lines[i + 1]
                # Même ordre de remplacement
                line_next_normalized = line_next.replace('O', '0').replace('o', '0')
                line_next_normalized = re.sub(r'S\s*0[\-/:,\.]', '60.', line_next_normalized)
                line_next_normalized = line_next_normalized.replace('S0', '60').replace('s0', '60')
                line_next_normalized = line_next_normalized.replace('S', '6').replace('s', '6')
                line_next_normalized = line_next_normalized.replace('d', '0').replace('D', '0')


                amounts_next = re.findall(r'([0-9]{1,4}[,\.\-/:][0-9]{2})', line_next_normalized)
                if amounts_next:
                    for amt_str in amounts_next:
                        try:
                            amount = float(amt_str.replace(',', '.').replace('-', '.').replace('/', '.').replace(':', '.'))
                            if 0.01 < amount < 10000:
                                print(f"Montant trouvé ligne après MONTANT REEL: {amount}€")
                                return amount
                        except ValueError:
                            continue

    # Patterns génériques avec mots-clés
    patterns = [
        r'TOTAL[:\s]+([0-9]+[,\.][0-9]{1,2})\s*(?:€|EUR)',
        r'MONTANT[:\s]+([0-9]+[,\.][0-9]{1,2})\s*(?:€|EUR)',
        r'CARTE[:\s]+([0-9]+[,\.][0-9]{1,2})\s*(?:€|EUR)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text_upper)
        for match in matches:
            amount_str = match if isinstance(match, str) else match[0]
            amount_str = amount_str.replace(' ', '').replace(',', '.')
            try:
                amount = float(amount_str)
                if 0.01 < amount < 10000:
                    print(f"Montant trouvé avec pattern '{pattern}': {amount}€")
                    return amount
            except ValueError:
                continue

    # Si aucun pattern trouvé, chercher tous les montants valides et prendre une décision
    all_amounts = re.findall(r'([0-9]{1,4}[,\.][0-9]{2})', text_upper)
    if all_amounts:
        amounts = []
        for a in all_amounts:
            try:
                val = float(a.replace(',', '.').replace(' ', ''))
                if 0.01 < val < 10000:
                    amounts.append(val)
            except ValueError:
                continue

        if amounts:
            # Prendre le montant le plus courant s'il y en a plusieurs identiques
            # Sinon prendre un montant médian (ni le plus petit ni le plus grand)
            from collections import Counter
            count = Counter(amounts)
            most_common = count.most_common(1)
            if most_common and most_common[0][1] > 1:
                print(f"Montant trouvé (le plus fréquent): {most_common[0][0]}€")
                return most_common[0][0]

            # Sinon, éviter les extrêmes et prendre un montant médian
            amounts.sort()
            if len(amounts) >= 3:
                # Éviter le plus petit et le plus grand, prendre celui du milieu
                median_amount = amounts[len(amounts) // 2]
                print(f"Montant trouvé (médian): {median_amount}€")
                return median_amount
            elif amounts:
                print(f"Montant trouvé (fallback): {amounts[-1]}€")
                return amounts[-1]

    return None


def parse_date(text: str) -> Optional[datetime]:
    """
    Cherche et extrait la date du reçu
    Formats acceptés : DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, etc.
    Très tolérant aux erreurs OCR
    """
    # Remplacer les erreurs OCR courantes pour les dates
    # Gérer spécifiquement d# → 14
    text_clean = text.replace('d#', '14').replace('D#', '14').replace('d4', '14')
    text_clean = text_clean.replace('O', '0').replace('o', '0').replace('Ô', '0').replace('Q', '0')
    text_clean = text_clean.replace('l', '1').replace('I', '1').replace('|', '1').replace('!', '1')
    text_clean = text_clean.replace('S', '5').replace('s', '5')
    text_clean = text_clean.replace('B', '8').replace('b', '8')
    text_clean = text_clean.replace('Z', '2').replace('z', '2')
    text_clean = text_clean.replace('?', '7').replace('T', '7')
    text_clean = text_clean.replace('G', '6').replace('g', '6')
    text_clean = text_clean.replace('d', '1').replace('D', '1')  # d peut être 1 (après d# → 14)
    text_clean = text_clean.replace('#', '4')  # # → 4

    # Chercher spécifiquement "Le DD-MM-YY" ou "Le DD/MM/YY" (format Intermarché)
    # Accepter aussi les erreurs type "14-01.56" pour "14-01-26"
    le_patterns = [
        r'[Ll][eE]?\s+(\d{1,2})[\-/\.\s](\d{1,2})[\-/\.\s](\d{2,4})',  # Le DD-MM-YY
        r'[Ll][eE]?\s+(\d{1,2})[\-/\.](\d{1,2})[\.\-/](\d{1,2})',  # Le DD-MM.YY (avec point)
    ]

    for le_pattern in le_patterns:
        match = re.search(le_pattern, text_clean)
        if match:
            try:
                day = match.group(1).strip()
                month = match.group(2).strip()
                year = match.group(3).strip()

                # Gérer les erreurs OCR sur l'année (ex: 56 au lieu de 26)
                if len(year) == 2:
                    year_int = int(year)
                    # Si l'année semble incorrecte (>26), essayer des corrections
                    if year_int > 30 and year_int < 60:
                        # Probablement une erreur OCR, essayer 26
                        year = '2026'
                        print(f"Correction année OCR: {year_int} -> 26")
                    elif year_int > 50:
                        year = '19' + year
                    else:
                        year = '20' + year

                # Vérifier les valeurs
                day_int = int(day)
                month_int = int(month)

                if day_int > 31 or month_int > 12:
                    continue

                date_obj = datetime(int(year), month_int, day_int)
                now = datetime.now()
                # Accepter les dates futures (jusqu'à 1 mois)
                if date_obj <= datetime(now.year + 1, now.month, now.day) and date_obj >= datetime(now.year - 5, 1, 1):
                    print(f"Date trouvée avec pattern 'Le': {date_obj.strftime('%d/%m/%Y')}")
                    return date_obj
            except (ValueError, AttributeError) as e:
                print(f"Erreur parsing date 'Le': {e}")
                continue

    # Patterns de dates (du plus spécifique au plus général)
    date_patterns = [
        # Format complet avec séparateurs
        r'(\d{1,2})[\-/\.\s](\d{1,2})[\-/\.\s](\d{4})',  # DD/MM/YYYY ou D/M/YYYY
        r'(\d{1,2})[\-/\.\s](\d{1,2})[\-/\.\s](\d{2})',  # DD/MM/YY
        # Format texte
        r'(\d{1,2})\s+(JAN|FEV|FEB|MAR|AVR|APR|MAI|MAY|JUN|JUI|JUL|AOU|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s+(\d{2,4})',
    ]

    # Mapping des mois texte
    month_map = {
        'JAN': 1, 'FEV': 2, 'FEB': 2, 'MAR': 3, 'AVR': 4, 'APR': 4,
        'MAI': 5, 'MAY': 5, 'JUN': 6, 'JUI': 7, 'JUL': 7,
        'AOU': 8, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }

    for pattern in date_patterns:
        matches = re.findall(pattern, text_clean.upper())
        for match in matches:
            try:
                if len(match) == 3:
                    day, month, year = match

                    # Si le mois est du texte
                    if isinstance(month, str) and month.isalpha():
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

                    # Vérifier que la date est raisonnable
                    now = datetime.now()
                    # Accepter les dates futures (jusqu'à 1 mois)
                    if date_obj <= datetime(now.year + 1, now.month, now.day) and date_obj >= datetime(now.year - 5, 1, 1):
                        print(f"Date trouvée: {date_obj.strftime('%d/%m/%Y')}")
                        return date_obj
            except (ValueError, AttributeError) as e:
                print(f"Erreur parsing date: {e}")
                continue

    return None


def parse_merchant_name(text: str) -> Optional[str]:
    """
    Essaie d'identifier le nom du commerçant
    Généralement en haut du reçu (premières lignes)
    Très tolérant aux erreurs OCR
    """
    text_upper = text.upper()

    # Normaliser les erreurs OCR courantes
    text_normalized = text_upper.replace('0', 'O').replace('1', 'I').replace('3', 'E')
    text_normalized = text_normalized.replace('|', 'I').replace('!', 'I')

    # Liste des commerçants connus avec variations OCR possibles
    known_merchants = {
        'INTERMARCHE': ['INTERMARCHE', 'INTER MARCHE', 'INTÉRMARCHÉ', 'LNTERMARCHE',
                        'INTERMARCHÉ', 'INTER MARCHÉ', 'INT3RMARCHE', 'INTERMÄRCHE'],
        'CARREFOUR': ['CARREFOUR', 'CARR3FOUR', 'CARRËFOUR'],
        'AUCHAN': ['AUCHAN', 'ÄUCHAN'],
        'LECLERC': ['LECLERC', 'E.LECLERC', 'E LECLERC', 'L3CLERC'],
        'LIDL': ['LIDL', 'L1DL'],
        'ALDI': ['ALDI', 'ALD1'],
        'CASINO': ['CASINO', 'CAS1NO'],
        'MONOPRIX': ['MONOPRIX', 'M0N0PRIX'],
        'FRANPRIX': ['FRANPRIX', 'FRANPR1X'],
        'BIOCOOP': ['BIOCOOP', 'B10COOP'],
        'SUPER U': ['SUPER U', 'SUP3R U'],
        'HYPER U': ['HYPER U', 'HYP3R U'],
        'TOTAL': ['TOTAL', 'T0TAL'],
        'BP': ['BP'],
        'SHELL': ['SHELL', 'SH3LL'],
        'ESSO': ['ESSO', '3SSO'],
        'MCDONALD': ['MCDONALD', 'MCDO', 'MCD0'],
        'KFC': ['KFC'],
        'DECATHLON': ['DECATHLON', 'D3CATHLON'],
        'LEROY MERLIN': ['LEROY MERLIN', 'L3ROY MERLIN'],
        'PHARMACIE': ['PHARMACIE', 'PHARMAC13'],
    }

    # Chercher un commerçant connu dans le texte (avec variations)
    for merchant_canonical, variations in known_merchants.items():
        for variation in variations:
            # Recherche flexible (tolère des espaces)
            pattern = variation.replace(' ', r'\s*')
            if re.search(pattern, text_upper):
                print(f"Commerçant trouvé: {merchant_canonical} (pattern: {variation})")
                return merchant_canonical.title()

    # Recherche de fragments spécifiques pour INTERMARCHE
    intermarche_patterns = [
        r'[ÉE][NM][TL][EI3][RP][MN][AI][RP]?\s*[CS][HCL][EI3]',  # ÉNTERMA CHE
        r'[AI][NM][TL][EI3][RP][MN][AI][RP][CS][HCL][EI3]',  # Pattern flexible
        r'[AI]NT[EI3]R.*MAR[CS]H',  # INTER...MARCH
        r'INT.*MAR.*CH',  # Fragments séparés
        r'[ÉE]NT.*MA.*CH',  # ÉNTE...MA...CH
        r'TERMA.*CH',  # TERMA...CH
    ]
    for pattern in intermarche_patterns:
        if re.search(pattern, text_upper):
            print(f"Commerçant trouvé (pattern flexible): INTERMARCHE")
            return "Intermarche"

    # Si pas de correspondance exacte, chercher des sous-chaînes
    for merchant_canonical, variations in known_merchants.items():
        for variation in variations:
            # Chercher des fragments (au moins 6 caractères consécutifs)
            if len(variation) >= 6:
                fragment = variation[:6]
                if fragment in text_upper or fragment in text_normalized:
                    print(f"Commerçant trouvé (fragment): {merchant_canonical}")
                    return merchant_canonical.title()

    # Fallback: analyser les premières lignes
    lines = text.split('\n')
    top_lines = [line.strip() for line in lines[:15] if line.strip() and len(line.strip()) > 3]

    if not top_lines:
        return None

    # Chercher spécifiquement les lignes qui ressemblent à un nom de magasin
    for line in top_lines:
        line_clean = re.sub(r'[^\w\s]', '', line).strip()
        # Si la ligne contient un mot long (>= 8 caractères), c'est probablement le commerçant
        words = line_clean.split()
        for word in words:
            if len(word) >= 8:
                # Vérifier si ça ressemble à INTERMARCHE
                if 'INTER' in word.upper() or 'MARCH' in word.upper():
                    print(f"Commerçant trouvé (mot-clé): {word}")
                    return 'Intermarche'
                # Retourner le mot long comme commerçant potentiel
                print(f"Commerçant potentiel: {word}")
                return word.title()

    # Le nom du commerçant est souvent la ligne la plus longue en haut
    merchant_candidates = [line for line in top_lines if len(line) > 5 and len(line) < 50]

    if merchant_candidates:
        merchant_name = max(merchant_candidates, key=len)
        merchant_name = re.sub(r'\s+', ' ', merchant_name).strip()
        merchant_name = re.sub(r'[^\w\s\-\']', '', merchant_name)
        return merchant_name[:100]

    return None


def guess_category(merchant_name: str) -> Optional[str]:
    """
    Devine la catégorie d'achat depuis le nom du commerçant
    """
    if not merchant_name:
        return None

    merchant_upper = merchant_name.upper()

    # Mapping commerçants → catégories (noms exacts des catégories en base)
    category_keywords = {
        'Alimentation': ['CARREFOUR', 'AUCHAN', 'LECLERC', 'LIDL', 'ALDI', 'INTERMARCHE',
                        'SUPER', 'MARKET', 'EPICERIE', 'BOULANGERIE', 'BOUCHERIE', 'MONOPRIX',
                        'FRANPRIX', 'CASINO', 'PICARD', 'FROMAGERIE'],
        'Carburant': ['TOTAL', 'BP', 'SHELL', 'ESSO', 'STATION', 'ESSENCE', 'CARBURANT',
                     'AGIP', 'PETROLE', 'GASOIL', 'DIESEL'],
        'Restaurant': ['RESTAURANT', 'CAFE', 'BRASSERIE', 'PIZZERIA', 'BURGER',
                      'MCDONALD', 'KFC', 'QUICK', 'BAR', 'BISTRO', 'SUSHI', 'KEBAB',
                      'SUBWAY', 'STARBUCKS', 'PAUL'],
        'Transport': ['SNCF', 'RATP', 'UBER', 'TAXI', 'METRO', 'BUS', 'TRAIN', 'PARKING',
                     'AUTOROUTE', 'PEAGE', 'VELIB', 'TRAMWAY'],
        'Santé & Pharmacie': ['PHARMACIE', 'HOPITAL', 'CLINIQUE', 'MEDECIN', 'DENTISTE',
                             'OPTICIEN', 'LABORATOIRE', 'SANTE'],
        'Loisirs & Culture': ['CINEMA', 'THEATRE', 'SPORT', 'GYM', 'PISCINE', 'CONCERT',
                             'MUSEE', 'SPECTACLE', 'FNAC', 'CULTURA'],
        'Habillement': ['ZARA', 'H&M', 'KIABI', 'MODE', 'VETEMENT', 'CHAUSSURES',
                       'JENNYFER', 'CELIO', 'JULES', 'CAMAIEU', 'PIMKIE'],
        'Maison & Jardin': ['LEROY', 'CASTORAMA', 'BRICORAMA', 'BRICO', 'IKEA', 'BUT',
                           'CONFORAMA', 'JARDIN', 'MAISON', 'BRICOLAGE'],
        'Électronique & High-tech': ['FNAC', 'DARTY', 'BOULANGER', 'APPLE', 'SAMSUNG',
                                     'MICRO', 'INFORMATIQUE', 'ORANGE', 'SFR', 'BOUYGUES'],
        'Sport & Fitness': ['DECATHLON', 'SPORT', 'FITNESS', 'GYM', 'YOGA', 'INTERSPORT',
                           'GO SPORT'],
        'Beauté & Cosmétiques': ['SEPHORA', 'NOCIBE', 'MARIONNAUD', 'COIFFEUR', 'BEAUTE',
                                'PARFUM', 'COSMETIQUE'],
        'Animaux': ['ANIMALERIE', 'VETERINAIRE', 'ANIMAL', 'MAXI ZOO', 'JARDILAND'],
    }

    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in merchant_upper:
                return category

    return 'Autre'


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
