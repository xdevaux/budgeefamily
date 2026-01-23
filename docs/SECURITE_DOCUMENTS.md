# 🔐 Guide de sécurité pour les documents uploadés

## État actuel de la sécurité

### ✅ Mesures existantes
- Authentification requise (`@login_required`)
- Contrôle d'accès par utilisateur (`user_id`)
- Limite de taille globale (16 MB)
- Stockage en base de données (isolation)

### ❌ Vulnérabilités critiques

#### 1. Aucune validation du type de fichier
**Risque** : Exécution de code malveillant, injection de scripts
**Impact** : CRITIQUE

#### 2. Injection de headers HTTP
**Risque** : XSS, manipulation de réponse HTTP
**Impact** : ÉLEVÉ

#### 3. Pas de rate limiting
**Risque** : Saturation de la base, déni de service
**Impact** : MOYEN

#### 4. Pas de scan antivirus
**Risque** : Malware dans les documents
**Impact** : ÉLEVÉ

#### 5. Noms de fichiers non sécurisés
**Risque** : Path traversal
**Impact** : MOYEN

---

## 🛡️ Plan d'action recommandé

### Priorité 1 - URGENT (à implémenter immédiatement)

#### 1.1 Validation stricte des fichiers

**Modifier** : `app/routes/banks.py`, `app/routes/employers.py`, `app/routes/credits.py`

```python
from app.utils.file_security import validate_upload, get_safe_content_disposition

# Dans add_document()
if 'file' in request.files:
    file = request.files['file']

    # ANCIENNE VERSION - DANGEREUX
    # if file and file.filename:
    #     document.file_data = file.read()

    # NOUVELLE VERSION - SÉCURISÉ
    success, error, file_data, safe_filename = validate_upload(file)

    if not success:
        flash(error, 'danger')
        return redirect(url_for('banks.add_document', bank_id=bank_id))

    document.file_data = file_data
    document.file_name = safe_filename
    document.file_mime_type = file.content_type
    document.file_size = len(file_data)
```

#### 1.2 Sécurisation des téléchargements

```python
from app.utils.file_security import get_safe_content_disposition

# Dans download_document() et view_document()
# ANCIENNE VERSION - VULNÉRABLE
# headers={'Content-Disposition': f'attachment; filename="{document.file_name}"'}

# NOUVELLE VERSION - SÉCURISÉ
return Response(
    document.file_data,
    mimetype=document.file_mime_type or 'application/octet-stream',
    headers={'Content-Disposition': get_safe_content_disposition(document.file_name, inline=False)}
)
```

#### 1.3 Rate limiting sur les uploads

**Installer** : `pip install Flask-Limiter`

**Ajouter dans** `app/__init__.py` :
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)
```

**Appliquer aux routes d'upload** :
```python
from app import limiter

@bp.route('/banks/<int:bank_id>/documents/add', methods=['GET', 'POST'])
@login_required
@limiter.limit("10 per hour")  # Max 10 uploads par heure
def add_document(bank_id):
    # ...
```

### Priorité 2 - IMPORTANT (à implémenter sous 1 semaine)

#### 2.1 Installation de python-magic pour vérification MIME

```bash
# Linux
sudo apt-get install libmagic1
pip install python-magic

# macOS
brew install libmagic
pip install python-magic
```

#### 2.2 Logging des uploads

**Créer** : `app/utils/security_logger.py`
```python
import logging
from datetime import datetime

security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)
handler = logging.FileHandler('logs/security.log')
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
security_logger.addHandler(handler)

def log_upload(user_id, filename, file_size, success, ip_address):
    """Log tous les uploads pour audit"""
    security_logger.info(
        f"UPLOAD - User:{user_id} | File:{filename} | "
        f"Size:{file_size} | Success:{success} | IP:{ip_address}"
    )

def log_download(user_id, document_id, ip_address):
    """Log tous les téléchargements"""
    security_logger.info(
        f"DOWNLOAD - User:{user_id} | Doc:{document_id} | IP:{ip_address}"
    )
```

#### 2.3 Surveillance des tentatives suspectes

```python
from app.utils.security_logger import log_upload, log_download
from flask import request

# Dans add_document()
log_upload(
    current_user.id,
    safe_filename,
    len(file_data),
    success=True,
    ip_address=request.remote_addr
)

# En cas d'échec de validation
if not success:
    log_upload(
        current_user.id,
        file.filename,
        0,
        success=False,
        ip_address=request.remote_addr
    )
```

### Priorité 3 - RECOMMANDÉ (à planifier)

#### 3.1 Scan antivirus avec ClamAV

```bash
# Installation
sudo apt-get install clamav clamav-daemon
pip install clamd
```

```python
import clamd

def scan_for_malware(file_data):
    """Scan le fichier pour détecter les malwares"""
    try:
        cd = clamd.ClamdUnixSocket()
        result = cd.scan_stream(file_data)
        return result is None  # None = pas de virus
    except Exception:
        # En cas d'erreur, on log et on accepte (à améliorer)
        return True
```

#### 3.2 Migration vers stockage fichier

Pour de meilleures performances :
- Stocker les fichiers sur disque ou S3
- Garder uniquement le chemin en base
- Utiliser des UUID pour les noms de fichiers

#### 3.3 Chiffrement des fichiers sensibles

```python
from cryptography.fernet import Fernet

def encrypt_file(file_data, key):
    """Chiffre les données du fichier"""
    f = Fernet(key)
    return f.encrypt(file_data)

def decrypt_file(encrypted_data, key):
    """Déchiffre les données du fichier"""
    f = Fernet(key)
    return f.decrypt(encrypted_data)
```

#### 3.4 Protection CSRF renforcée

Déjà en place avec Flask-WTF, mais vérifier :
```python
# Dans les templates
<form method="POST" enctype="multipart/form-data">
    {{ form.csrf_token }}
    <!-- ... -->
</form>
```

#### 3.5 Headers de sécurité HTTP

**Ajouter dans** `app/__init__.py` :
```python
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

---

## 📋 Checklist d'implémentation

### Immédiat (cette semaine)
- [ ] Créer `app/utils/file_security.py`
- [ ] Intégrer `validate_upload()` dans toutes les routes d'upload
- [ ] Sécuriser les headers avec `get_safe_content_disposition()`
- [ ] Installer Flask-Limiter
- [ ] Ajouter rate limiting sur les uploads

### Court terme (2 semaines)
- [ ] Installer python-magic
- [ ] Créer le système de logging de sécurité
- [ ] Logger tous les uploads/downloads
- [ ] Créer un dashboard d'audit pour les admins

### Moyen terme (1 mois)
- [ ] Installer ClamAV
- [ ] Intégrer le scan antivirus
- [ ] Migrer vers stockage fichier (optionnel)
- [ ] Ajouter chiffrement pour documents sensibles

### Long terme
- [ ] Audit de sécurité externe
- [ ] Tests de pénétration
- [ ] Documentation utilisateur sur la sécurité

---

## 🚨 Incidents à surveiller

### Indicateurs de tentatives d'attaque
1. **Uploads massifs** : > 20 fichiers/heure d'un même utilisateur
2. **Fichiers suspects** : Extensions multiples (.pdf.exe)
3. **Noms malveillants** : ../../../etc/passwd
4. **Tailles anormales** : Fichiers de 0 byte ou > 15 MB
5. **Types MIME incohérents** : Extension .pdf mais MIME application/x-executable

### Actions automatiques recommandées
- Bloquer temporairement l'utilisateur après 5 tentatives suspectes
- Alerter les admins par email
- Marquer le compte pour vérification manuelle

---

## 📚 Ressources complémentaires

- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)

---

## ⚠️ IMPORTANT

**NE PAS** faire confiance uniquement à :
- L'extension du fichier (facilement falsifiable)
- Le MIME type envoyé par le client (peut être modifié)
- La taille déclarée (vérifier le contenu réel)

**TOUJOURS** :
- Valider côté serveur
- Vérifier le contenu réel du fichier
- Logger les activités suspectes
- Limiter les ressources (taille, nombre)
- Isoler les fichiers uploadés
