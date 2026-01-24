"""
Module de sécurité pour la gestion des fichiers uploadés
"""
import os
import re
import hashlib
import magic
from werkzeug.utils import secure_filename
from flask import current_app

# Extensions autorisées pour les documents
ALLOWED_DOCUMENT_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'xls', 'xlsx',
    'odt', 'ods', 'txt', 'csv',
    'jpg', 'jpeg', 'png', 'gif', 'webp'
}

# MIME types autorisés (vérification réelle du contenu)
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.oasis.opendocument.text',
    'application/vnd.oasis.opendocument.spreadsheet',
    'text/plain',
    'text/csv',
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp'
}

# Taille maximale par type de fichier (en bytes)
MAX_FILE_SIZES = {
    'pdf': 10 * 1024 * 1024,      # 10MB pour PDF
    'image': 5 * 1024 * 1024,      # 5MB pour images
    'document': 15 * 1024 * 1024,  # 15MB pour documents Office
    'text': 1 * 1024 * 1024        # 1MB pour texte
}


def is_allowed_extension(filename):
    """Vérifie si l'extension du fichier est autorisée"""
    if not filename or '.' not in filename:
        return False

    extension = filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_DOCUMENT_EXTENSIONS


def is_allowed_mime_type(file_data):
    """Vérifie le MIME type réel du fichier (pas seulement l'extension)"""
    try:
        mime = magic.from_buffer(file_data, mime=True)
        return mime in ALLOWED_MIME_TYPES
    except Exception:
        # Si python-magic n'est pas installé, on accepte (à améliorer)
        return True


def sanitize_filename(filename):
    """Nettoie et sécurise le nom de fichier"""
    # Utilise secure_filename de werkzeug
    safe_name = secure_filename(filename)

    # Remplace les caractères non-ASCII
    safe_name = re.sub(r'[^\w\s\-\.]', '', safe_name)

    # Limite la longueur
    name, ext = os.path.splitext(safe_name)
    if len(name) > 100:
        name = name[:100]

    return f"{name}{ext}"


def generate_secure_filename(original_filename, user_id):
    """Génère un nom de fichier unique et sécurisé"""
    # Récupère l'extension
    _, ext = os.path.splitext(original_filename)

    # Génère un hash unique
    timestamp = str(os.urandom(16).hex())
    unique_id = hashlib.sha256(f"{user_id}{timestamp}".encode()).hexdigest()[:16]

    return f"{unique_id}{ext.lower()}"


def validate_file_size(file_data, file_type='document'):
    """Vérifie que la taille du fichier est acceptable"""
    size = len(file_data)
    max_size = MAX_FILE_SIZES.get(file_type, 10 * 1024 * 1024)

    return size <= max_size


def escape_header_value(value):
    """Échappe les valeurs pour les headers HTTP (prévient injection)"""
    if not value:
        return ""

    # Supprime les caractères dangereux
    safe_value = re.sub(r'["\r\n]', '', value)

    # Limite la longueur
    if len(safe_value) > 255:
        safe_value = safe_value[:255]

    return safe_value


def validate_upload(file, allowed_extensions=None, max_size=None):
    """
    Validation complète d'un fichier uploadé

    Returns:
        tuple: (success: bool, error_message: str, file_data: bytes, safe_filename: str)
    """
    if not file or not file.filename:
        return False, "Aucun fichier sélectionné", None, None

    original_filename = file.filename

    # 1. Validation de l'extension
    if not is_allowed_extension(original_filename):
        return False, "Type de fichier non autorisé. Formats acceptés : PDF, Word, Excel, Images", None, None

    # 2. Lecture du fichier
    try:
        file_data = file.read()
    except Exception as e:
        return False, f"Erreur lors de la lecture du fichier : {str(e)}", None, None

    # 3. Vérification de la taille
    if not validate_file_size(file_data):
        size_mb = len(file_data) / (1024 * 1024)
        return False, f"Fichier trop volumineux ({size_mb:.1f} MB). Maximum : 15 MB", None, None

    # 4. Vérification du MIME type réel (détection de contenu)
    if not is_allowed_mime_type(file_data):
        return False, "Le contenu du fichier ne correspond pas à l'extension", None, None

    # 5. Génération d'un nom de fichier sécurisé
    safe_filename = sanitize_filename(original_filename)

    return True, None, file_data, safe_filename


def get_safe_content_disposition(filename, inline=False):
    """Génère un header Content-Disposition sécurisé"""
    safe_filename = escape_header_value(filename)
    disposition = "inline" if inline else "attachment"

    # Utilise à la fois filename et filename* (RFC 5987 pour les noms non-ASCII)
    return f'{disposition}; filename="{safe_filename}"; filename*=UTF-8\'\'{safe_filename}'
