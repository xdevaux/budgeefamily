# Guide de démarrage rapide - Subly Cloud

Ce guide vous permet de lancer l'application en 5 minutes.

## Étape 1 : Prérequis

Assurez-vous d'avoir :
- Python 3.12+ installé
- PostgreSQL installé et en cours d'exécution
- Une base de données `subly_app` créée

## Étape 2 : Créer la base de données PostgreSQL

```bash
# Connexion à PostgreSQL
sudo -u postgres psql

# Créer la base de données
CREATE DATABASE subly_app;

# Quitter PostgreSQL
\q
```

## Étape 3 : Activer l'environnement virtuel

```bash
source .venv/bin/activate
```

## Étape 4 : Installer les dépendances

```bash
pip install -r requirements.txt
```

## Étape 5 : Vérifier le fichier .env

Le fichier `.env` a déjà été créé avec des valeurs par défaut. Vérifiez que la variable `DATABASE_URL` correspond à votre configuration PostgreSQL.

Si vous utilisez un utilisateur/mot de passe PostgreSQL différent :
```env
DATABASE_URL=postgresql://username:password@localhost/subly_app
```

## Étape 6 : Initialiser la base de données

```bash
python init_db.py
```

Ce script va créer toutes les tables et ajouter les données de base (plans et catégories).

## Étape 7 : Lancer l'application

```bash
python run.py
```

## Étape 8 : Accéder à l'application

Ouvrez votre navigateur et allez sur : **http://localhost:5000**

## Étape 9 : Créer votre premier compte

1. Cliquez sur "S'inscrire"
2. Remplissez le formulaire
3. Vous êtes automatiquement connecté avec le plan gratuit
4. Ajoutez votre premier abonnement !

## Configuration optionnelle

### Pour activer Stripe (paiements Premium)

1. Créez un compte sur [Stripe](https://dashboard.stripe.com/)
2. Récupérez vos clés API (mode test)
3. Ajoutez-les dans le fichier `.env` :
   ```env
   STRIPE_PUBLIC_KEY=pk_test_...
   STRIPE_SECRET_KEY=sk_test_...
   ```
4. Créez un produit "Subly Cloud Premium" à 4.99€/mois
5. Mettez à jour le `stripe_price_id` dans la base de données

### Pour activer Google OAuth

1. Créez un projet sur [Google Cloud Console](https://console.cloud.google.com/)
2. Activez l'API Google+
3. Créez des identifiants OAuth 2.0
4. Ajoutez `http://localhost:5000/auth/google/callback` dans les URI de redirection
5. Ajoutez les identifiants dans `.env` :
   ```env
   GOOGLE_CLIENT_ID=votre_client_id
   GOOGLE_CLIENT_SECRET=votre_client_secret
   ```

## Problèmes courants

### Erreur de connexion à PostgreSQL
```
sqlalchemy.exc.OperationalError: could not connect to server
```
**Solution** : Vérifiez que PostgreSQL est en cours d'exécution et que la base de données `subly_app` existe.

### Module non trouvé
```
ModuleNotFoundError: No module named 'flask'
```
**Solution** : Assurez-vous que l'environnement virtuel est activé et que les dépendances sont installées.

### Port 5000 déjà utilisé
**Solution** : Modifiez le port dans `run.py` (ligne `app.run(..., port=5001)`)

## Commandes utiles

```bash
# Activer l'environnement virtuel
source .venv/bin/activate

# Lancer l'application
python run.py

# Réinitialiser la base de données
python init_db.py

# Accéder au shell Flask
flask shell
```

## Prochaines étapes

- Ajoutez vos premiers abonnements
- Explorez les catégories
- Consultez vos statistiques
- Testez le plan Premium (en mode test Stripe)

Pour plus d'informations, consultez le [README.md](README.md) complet.
