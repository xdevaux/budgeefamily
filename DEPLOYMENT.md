# Guide de déploiement en production - Subly Cloud

## Initialisation de la base de données

### 1. Appliquer les migrations

Avant toute chose, assurez-vous que toutes les migrations sont appliquées :

```bash
flask db upgrade
```

### 2. Initialiser l'application (plans + admin)

Le script `init_production.py` crée automatiquement :
- Les 3 plans de base (Free, Premium, Premium Annual)
- L'utilisateur administrateur avec le plan Premium

#### Configuration des variables d'environnement

**Obligatoire :**
```bash
export ADMIN_PASSWORD='VotreMotDePasseSecurisé123!'
```

**Optionnel (valeurs par défaut) :**
```bash
export ADMIN_EMAIL='contact@subly.cloud'
export ADMIN_FIRST_NAME='Admin'
export ADMIN_LAST_NAME='Subly Cloud'
```

#### Exécution du script

```bash
python init_production.py
```

#### Exemple de sortie

```
============================================================
  INITIALISATION DE L'APPLICATION SUBLY CLOUD - PRODUCTION
============================================================

=== Initialisation des plans ===

✅ Plan 'Free' créé.
✅ Plan 'Premium' créé.
✅ Plan 'Premium Annual' créé.

✅ 3 plan(s) créé(s) : Free, Premium, Premium Annual

=== Initialisation de l'administrateur ===

✅ Administrateur créé avec succès !
   Email : contact@subly.cloud
   Nom : Admin Subly Cloud
   Plan : Premium
   Administrateur : Oui
   Email vérifié : Oui

============================================================
  ✅ INITIALISATION TERMINÉE AVEC SUCCÈS
============================================================

⚠️  IMPORTANT :
   - Conservez le mot de passe administrateur en lieu sûr
   - Changez le mot de passe après la première connexion
   - Ne partagez jamais vos identifiants admin
```

## Script alternatif (admin uniquement)

Si vous souhaitez créer uniquement l'administrateur (les plans existent déjà) :

```bash
python init_admin.py
```

## Après le déploiement

### 1. Première connexion

1. Accédez à votre application : `https://votre-domaine.com/auth/login`
2. Connectez-vous avec les identifiants admin
3. Allez dans **Mon profil** et changez le mot de passe

### 2. Vérification

Dans le menu utilisateur, vous devriez voir :
- **Mon profil**
- **Plans & Tarifs**
- **Administration** (section dédiée)
  - Tableau de bord
  - Clients

### 3. Gestion des clients

Depuis l'interface admin, vous pouvez :
- ✅ Voir tous les clients inscrits
- ✅ Filtrer par statut (actifs/inactifs/tous)
- ✅ Ajouter de nouveaux clients
- ✅ Modifier les clients existants
- ✅ Supprimer des clients (avec suppression en cascade de leurs données)
- ✅ Assigner/modifier les plans
- ✅ Activer/désactiver des comptes
- ✅ Gérer les droits administrateur

### 4. Tableau de bord admin

Le tableau de bord affiche :
- Nombre total d'utilisateurs
- Nombre de comptes actifs
- Nombre d'administrateurs
- Répartition par plan avec revenus mensuels estimés
- Total des revenus mensuels
- Utilisateurs récents

## Scripts disponibles

| Script | Description | Variables requises |
|--------|-------------|-------------------|
| `init_production.py` | Initialisation complète (plans + admin) | `ADMIN_PASSWORD` |
| `init_admin.py` | Création admin uniquement | `ADMIN_PASSWORD` |
| `set_admin.py` | Mettre à jour un utilisateur existant comme admin | Aucune |
| `fix_is_admin_null.py` | Corriger les valeurs NULL dans is_admin | Aucune |
| `test_cascade_delete.py` | Tester la suppression en cascade | Aucune |
| `debug_users.py` | Déboguer les utilisateurs et plans | Aucune |

## Sécurité

### Mots de passe

- ✅ Utilisez des mots de passe forts (minimum 12 caractères)
- ✅ Incluez majuscules, minuscules, chiffres et symboles
- ✅ Ne stockez jamais les mots de passe en clair dans le code
- ✅ Utilisez des variables d'environnement ou un gestionnaire de secrets

### Variables d'environnement en production

Pour un déploiement sur Heroku, Railway, Render, etc. :

```bash
# Dans votre plateforme de déploiement, configurez :
ADMIN_PASSWORD=VotreMotDePasseSecurisé123!
ADMIN_EMAIL=contact@subly.cloud
ADMIN_FIRST_NAME=Admin
ADMIN_LAST_NAME=Subly Cloud
```

### En local (développement)

Créez un fichier `.env` (déjà dans .gitignore) :

```env
ADMIN_PASSWORD=VotreMotDePasseDev123!
ADMIN_EMAIL=admin@localhost
```

Puis chargez-le avant d'exécuter le script :

```bash
set -a
source .env
set +a
python init_production.py
```

## Commandes utiles

### Réinitialiser complètement la base de données

⚠️ **ATTENTION : Cela supprime TOUTES les données !**

```bash
flask db downgrade base
flask db upgrade
python init_production.py
```

### Vérifier l'état des migrations

```bash
flask db current
flask db history
```

### Créer une nouvelle migration

```bash
flask db migrate -m "description de la modification"
flask db upgrade
```

## Support

Pour toute question ou problème lors du déploiement, vérifiez :
1. Les logs de l'application
2. Les migrations sont bien appliquées (`flask db current`)
3. Les variables d'environnement sont correctement définies
4. La connexion à la base de données fonctionne
