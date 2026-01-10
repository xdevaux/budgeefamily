# Subly Cloud - Gestionnaire d'abonnements

Application web Python Flask pour gérer et suivre vos abonnements mensuels.

## Fonctionnalités

- **Gestion des abonnements** : Ajoutez, modifiez et suivez tous vos abonnements
- **Catégories** : Organisez vos abonnements par catégories (Streaming, Cloud, etc.)
- **Statistiques détaillées** : Visualisez vos dépenses avec des graphiques
- **Notifications** : Recevez des alertes avant les renouvellements
- **Plans tarifaires** :
  - **Gratuit** : Jusqu'à 5 abonnements
  - **Premium** : Abonnements illimités (4.99€/mois)
- **Authentification sécurisée** :
  - Email/Mot de passe
  - OAuth Google
  - (Apple OAuth à venir)
- **Paiements Stripe** : Intégration complète pour le plan Premium

## Technologies utilisées

- **Backend** : Flask 3.0
- **Base de données** : PostgreSQL
- **ORM** : SQLAlchemy
- **Authentification** : Flask-Login + OAuth (Authlib)
- **Paiements** : Stripe
- **Frontend** : Bootstrap 5 + Chart.js
- **Migrations** : Flask-Migrate

## Prérequis

- Python 3.12+
- PostgreSQL
- Compte Stripe (pour les paiements)
- Compte Google Cloud (pour OAuth Google)

## Installation

### 1. Cloner le projet

```bash
cd /home/xavierdx/app.subly.cloud
```

### 2. Créer et activer l'environnement virtuel

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer la base de données PostgreSQL

```bash
# Connexion à PostgreSQL
sudo -u postgres psql

# Créer la base de données (si elle n'existe pas déjà)
CREATE DATABASE subly_app;

# Créer un utilisateur (optionnel)
CREATE USER subly_user WITH PASSWORD 'votre_mot_de_passe';
GRANT ALL PRIVILEGES ON DATABASE subly_app TO subly_user;

\q
```

### 5. Configurer les variables d'environnement

Copiez le fichier `.env.example` en `.env` :

```bash
cp .env.example .env
```

Modifiez le fichier `.env` avec vos informations :

```env
DATABASE_URL=postgresql://username:password@localhost/subly_app
SECRET_KEY=votre-clé-secrète-très-longue-et-aléatoire
FLASK_APP=run.py
FLASK_ENV=development

# Stripe (https://dashboard.stripe.com/apikeys)
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Google OAuth (https://console.cloud.google.com/)
GOOGLE_CLIENT_ID=votre_google_client_id
GOOGLE_CLIENT_SECRET=votre_google_client_secret
```

### 6. Initialiser la base de données

```bash
python init_db.py
```

Ce script va :
- Créer toutes les tables
- Ajouter les plans (Free et Premium)
- Ajouter les catégories par défaut

### 7. (Optionnel) Configurer les migrations

Si vous voulez utiliser Flask-Migrate pour gérer les migrations :

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

## Configuration Stripe

### 1. Créer les produits dans Stripe

1. Connectez-vous à votre [Dashboard Stripe](https://dashboard.stripe.com/)
2. Allez dans **Produits** > **Ajouter un produit**
3. Créez un produit "Subly Cloud Premium" :
   - Prix : 4.99 EUR
   - Type : Abonnement récurrent mensuel
4. Copiez l'ID du prix (commence par `price_...`)
5. Mettez à jour la base de données :

```python
# Dans un shell Python avec le contexte Flask
from app import create_app, db
from app.models import Plan

app = create_app()
with app.app_context():
    premium = Plan.query.filter_by(name='Premium').first()
    premium.stripe_price_id = 'price_VOTRE_ID_STRIPE'
    db.session.commit()
```

### 2. Configurer les Webhooks Stripe

1. Dans le Dashboard Stripe : **Développeurs** > **Webhooks**
2. Ajoutez un endpoint : `https://votre-domaine.com/api/webhook`
3. Sélectionnez les événements :
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
4. Copiez le secret du webhook dans `.env`

## Configuration OAuth Google

1. Allez sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créez un nouveau projet ou sélectionnez-en un
3. Activez l'API "Google+ API"
4. Créez des identifiants OAuth 2.0 :
   - Type : Application Web
   - URI de redirection autorisées : `http://localhost:5000/auth/google/callback`
5. Copiez le Client ID et Client Secret dans `.env`

## Lancement de l'application

```bash
python run.py
```

L'application sera accessible sur : `http://localhost:5000`

## Utilisation

### Créer un compte

1. Allez sur `http://localhost:5000`
2. Cliquez sur "S'inscrire"
3. Remplissez le formulaire ou utilisez Google OAuth
4. Vous êtes automatiquement sur le plan gratuit

### Ajouter un abonnement

1. Connectez-vous
2. Cliquez sur "Ajouter un abonnement"
3. Remplissez les informations :
   - Nom (ex: Netflix)
   - Montant (ex: 12.99)
   - Périodicité (mensuel, annuel, hebdomadaire)
   - Catégorie
   - Date de début
4. L'abonnement apparaît dans votre dashboard

### Passer à Premium

1. Allez dans "Plans & Tarifs"
2. Cliquez sur "Passer à Premium"
3. Complétez le paiement via Stripe
4. Vous pouvez maintenant ajouter un nombre illimité d'abonnements

## Structure du projet

```
app.subly.cloud/
├── app/
│   ├── __init__.py          # Initialisation Flask
│   ├── models.py            # Modèles SQLAlchemy
│   ├── routes/              # Routes et vues
│   │   ├── auth.py          # Authentification
│   │   ├── main.py          # Pages principales
│   │   ├── subscriptions.py # Gestion abonnements
│   │   └── api.py           # API et webhooks Stripe
│   ├── templates/           # Templates HTML
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── auth/
│   │   ├── subscriptions/
│   │   └── categories/
│   └── static/              # CSS, JS, images
├── config.py                # Configuration
├── run.py                   # Point d'entrée
├── init_db.py              # Script initialisation DB
├── requirements.txt         # Dépendances Python
└── .env                     # Variables d'environnement
```

## Modèles de données

### User
- Informations utilisateur
- Authentification (email/password ou OAuth)
- Plan actuel
- Informations Stripe

### Plan
- Plans tarifaires (Free, Premium)
- Prix et fonctionnalités

### Subscription
- Abonnements de l'utilisateur
- Montant, périodicité
- Dates de facturation

### Category
- Catégories d'abonnements
- Logo, couleur, icône

### Notification
- Notifications utilisateur
- Alertes de renouvellement

## API Endpoints

- `POST /api/create-checkout-session` - Créer une session Stripe
- `GET /api/checkout/success` - Callback succès paiement
- `POST /api/create-portal-session` - Portail gestion abonnement
- `POST /api/webhook` - Webhooks Stripe
- `GET /api/stats` - Statistiques utilisateur

## Développement futur

- [ ] Application mobile (iOS et Android)
- [ ] Export PDF/CSV des abonnements
- [ ] Rappels par email
- [ ] Partage de compte famille
- [ ] Support multi-devises
- [ ] Intégration bancaire (agrégateurs)
- [ ] Détection automatique d'abonnements

## Sécurité

- Mots de passe hashés avec Werkzeug
- Protection CSRF avec Flask-WTF
- Authentification OAuth sécurisée
- Aucune donnée bancaire stockée (géré par Stripe)
- Variables sensibles dans `.env` (non versionné)

## Support

Pour toute question ou problème :
- Créer une issue sur GitHub
- Email : support@subly.cloud

## Licence

Tous droits réservés - Subly Cloud 2025
