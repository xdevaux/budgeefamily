# Checklist de déploiement - "Mes achats CB"

## ✅ Éléments complétés

### Installation système
- [x] Tesseract OCR 5.3.4 installé
- [x] Pack langue française (tesseract-ocr-fra) installé
- [x] Dépendances Python installées (pytesseract, opencv-python-headless, numpy)
- [x] Test OCR validé

### Base de données
- [x] Modèle `CardPurchase` ajouté à `app/models.py`
- [x] Migration créée (`1c7fdfad036e_add_card_purchases_table.py`)
- [x] Migration appliquée à la base de données
- [x] Table `card_purchases` créée avec tous les index

### Code backend
- [x] Module OCR (`app/utils/ocr_processor.py`) créé
- [x] Blueprint Flask (`app/routes/card_purchases.py`) créé
- [x] Blueprint enregistré dans `app/__init__.py`
- [x] 9 routes fonctionnelles (liste, upload, validation, détail, édition, suppression, etc.)

### Templates
- [x] `upload.html` - Formulaire d'upload
- [x] `validate.html` - Grille de validation
- [x] `list.html` - Liste des achats
- [x] `detail.html` - Détail d'un achat
- [x] `edit.html` - Édition d'un achat
- [x] Menu intégré dans `base.html`

### Documentation
- [x] Guide utilisateur (`docs/MES_ACHATS_CB.md`)
- [x] Résumé d'implémentation (`IMPLEMENTATION_SUMMARY_ACHATS_CB.md`)
- [x] Script de test OCR (`test_ocr.py`)

### Application
- [x] Application Flask redémarrée
- [x] Chargement sans erreur vérifié

## 🧪 Tests à effectuer (manuel)

### Tests fonctionnels de base
- [ ] Se connecter à l'application
- [ ] Naviguer vers "Dépenses > Mes achats CB"
- [ ] Vérifier que la page liste s'affiche

### Test d'upload simple
- [ ] Cliquer sur "Ajouter des achats"
- [ ] Uploader 1 image de reçu
- [ ] Vérifier que le traitement OCR s'exécute
- [ ] Vérifier que la grille de validation s'affiche
- [ ] Vérifier l'extraction : date, montant, commerçant, catégorie
- [ ] Modifier une donnée dans la grille
- [ ] Enregistrer
- [ ] Vérifier que l'achat apparaît dans la liste
- [ ] Vérifier qu'une transaction a été créée dans la balance

### Test d'upload multiple
- [ ] Uploader 3-5 reçus simultanément
- [ ] Vérifier le traitement de tous les fichiers
- [ ] Désélectionner un achat (décocher la case)
- [ ] Enregistrer
- [ ] Vérifier que seuls les achats cochés sont enregistrés

### Test de modification
- [ ] Ouvrir un achat existant
- [ ] Cliquer sur "Modifier"
- [ ] Changer le montant, la date, la catégorie
- [ ] Enregistrer
- [ ] Vérifier les modifications dans le détail
- [ ] Vérifier que la transaction dans la balance est mise à jour

### Test de suppression
- [ ] Ouvrir un achat
- [ ] Cliquer sur "Supprimer"
- [ ] Confirmer
- [ ] Vérifier que l'achat n'apparaît plus dans la liste
- [ ] Vérifier que la transaction est passée en statut "cancelled"

### Test de visualisation du reçu
- [ ] Ouvrir un achat avec image
- [ ] Cliquer sur l'icône "image" ou "Voir le reçu"
- [ ] Vérifier que l'image s'affiche correctement

### Test des filtres
- [ ] Filtrer par catégorie
- [ ] Filtrer par mois
- [ ] Filtrer par année
- [ ] Vérifier que le total du mois est correct

### Test de qualité OCR
- [ ] Tester avec un reçu très net (photo HD)
  - [ ] Vérifier confiance OCR > 80% (badge vert)
- [ ] Tester avec un reçu flou ou mal éclairé
  - [ ] Vérifier confiance OCR < 50% (badge rouge)
- [ ] Vérifier que les données peu fiables peuvent être corrigées manuellement

### Test de sécurité
- [ ] Essayer d'uploader un fichier non-image (ex: .exe, .sh)
  - [ ] Vérifier que le fichier est rejeté
- [ ] Essayer d'uploader un fichier > 5 Mo
  - [ ] Vérifier que le fichier est rejeté
- [ ] Essayer d'uploader plus de 10 fichiers
  - [ ] Vérifier le message d'avertissement

### Test de performance
- [ ] Uploader 10 images simultanément
- [ ] Mesurer le temps de traitement
- [ ] Vérifier qu'il n'y a pas d'erreur de timeout

## 🔍 Points de vérification technique

### Logs
```bash
# Vérifier les logs d'erreur Flask
tail -f /var/log/budgeefamily/error.log

# Si des erreurs OCR apparaissent, vérifier :
# - Tesseract est bien installé : tesseract --version
# - Les permissions sur /usr/bin/tesseract
```

### Base de données
```sql
-- Vérifier la structure de la table
\d card_purchases

-- Vérifier quelques données
SELECT id, merchant_name, amount, purchase_date, ocr_confidence
FROM card_purchases
LIMIT 5;

-- Vérifier les transactions associées
SELECT t.* FROM transactions t
WHERE t.source_type = 'card_purchase';
```

### Performance
```python
# Tester le temps de traitement OCR
python test_ocr.py

# Si trop lent, vérifier :
# - Taille des images (redimensionner si > 2000px)
# - Qualité de prétraitement
# - Charge CPU/RAM du serveur
```

## 🚨 Problèmes potentiels et solutions

### Erreur : "Tesseract not found"
```bash
# Vérifier l'installation
which tesseract

# Réinstaller si nécessaire
sudo apt-get install tesseract-ocr tesseract-ocr-fra
```

### Erreur : "Language 'fra' not found"
```bash
# Installer le pack français
sudo apt-get install tesseract-ocr-fra

# Vérifier les langues disponibles
tesseract --list-langs
```

### Erreur : "ImportError: numpy"
```bash
# Downgrade NumPy
source .venv/bin/activate
pip install "numpy<2"
```

### Erreur : "libGL.so.1 not found"
```bash
# Vous utilisez opencv-python au lieu de opencv-python-headless
source .venv/bin/activate
pip uninstall opencv-python
pip install opencv-python-headless==4.9.0.80
```

### OCR ne détecte rien
- Vérifier la qualité de l'image (netteté, éclairage)
- Essayer de recadrer l'image
- Vérifier que le texte est en français
- Les reçus thermiques (tickets de caisse) peuvent être difficiles à lire s'ils sont vieux

### Lenteur du traitement
- Redimensionner les images avant upload (< 2 Mo recommandé)
- Limiter le nombre d'uploads simultanés à 5
- Considérer l'ajout d'un traitement asynchrone (Celery)

## 📝 Notes de déploiement

### Variables d'environnement
Aucune nouvelle variable nécessaire. Tesseract utilise le chemin par défaut `/usr/bin/tesseract`.

### Permissions
Vérifier que l'utilisateur de l'application (xavierdx) a accès à :
- `/usr/bin/tesseract`
- `/usr/share/tesseract-ocr/` (données OCR)

### Sauvegarde
Avant le déploiement en production :
```bash
# Sauvegarder la base de données
pg_dump budgeefamily > backup_before_card_purchases.sql

# Sauvegarder le code
git commit -am "Add card purchases OCR feature"
```

### Rollback si nécessaire
```bash
# Annuler la migration
source .venv/bin/activate
flask db downgrade

# Redémarrer l'application
kill -HUP $(pgrep -f "gunicorn.*wsgi:app" | head -1)
```

## ✅ Validation finale

- [ ] Tous les tests fonctionnels passent
- [ ] Aucune erreur dans les logs
- [ ] Performance acceptable (< 30s pour 10 images)
- [ ] Données correctement enregistrées en base
- [ ] Transactions créées dans la balance
- [ ] Menu "Mes achats CB" visible et fonctionnel
- [ ] Documentation accessible

## 🎉 Mise en production

Une fois tous les tests validés :

1. Informer les utilisateurs de la nouvelle fonctionnalité
2. Fournir le guide utilisateur (`docs/MES_ACHATS_CB.md`)
3. Surveiller les logs pendant les premières 24h
4. Collecter les retours utilisateurs

**Date de déploiement** : _______________
**Validé par** : _______________
**Notes** : _______________
