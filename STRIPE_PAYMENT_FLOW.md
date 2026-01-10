# Flux de paiement Stripe - Subly Cloud

## Vue d'ensemble

Le système de paiement Stripe permet aux utilisateurs de souscrire aux plans Premium (mensuel ou annuel) de Subly Cloud. Ce document décrit les différents flux de paiement disponibles.

## Plans disponibles

### 1. Plan Free (Gratuit)
- Prix : 0€
- Limite : 5 abonnements
- Période d'essai Premium : 7 jours offerts à l'inscription

### 2. Plan Premium (Mensuel)
- Prix : 4.99€/mois
- Abonnements illimités
- Facturation mensuelle via Stripe

### 3. Plan Premium Annual (Annuel)
- Prix : 49.99€/an
- Abonnements illimités
- Économie de 2 mois (9.89€)
- Facturation annuelle via Stripe

## Configuration Stripe requise

### Variables d'environnement

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Configuration des plans dans la base de données

Chaque plan Premium doit avoir un `stripe_price_id` configuré :

```sql
-- Plan Premium Mensuel
UPDATE plans SET stripe_price_id = 'price_xxx' WHERE name = 'Premium';

-- Plan Premium Annuel
UPDATE plans SET stripe_price_id = 'price_yyy' WHERE name = 'Premium Annual';
```

Ces `stripe_price_id` sont créés dans le Dashboard Stripe sous "Produits et prix".

## Flux de paiement

### Flux 1 : Inscription directe avec Premium

**Scénario** : L'utilisateur clique sur "Commencer avec Premium" ou "Commencer avec Premium Annuel" depuis la page de tarification sans être connecté.

**Étapes** :

1. **Page de tarification** (`/pricing`)
   - L'utilisateur clique sur "Commencer avec Premium" ou "Commencer avec Premium Annuel"
   - Redirection vers `/auth/register?plan=premium` ou `/auth/register?plan=premium-annual`

2. **Formulaire d'inscription** (`/auth/register`)
   - Le formulaire affiche un message adapté : "Vous vous inscrivez pour le plan Premium"
   - **Pas de période d'essai de 7 jours** pour les inscriptions Premium directes
   - L'utilisateur remplit ses informations (email, mot de passe, devise)
   - Le plan choisi est stocké dans la session : `session['pending_premium_plan'] = 'monthly'` ou `'yearly'`

3. **Après inscription**
   - Un email de vérification est envoyé (sans mention de l'essai gratuit)
   - Message flash : "Vous pourrez finaliser votre paiement Premium après avoir vérifié votre email"
   - Redirection vers `/auth/login`

4. **Première connexion** (`/auth/login`)
   - Après connexion, détection du plan en attente dans la session
   - Redirection automatique vers `/checkout-redirect?plan=monthly` ou `?plan=yearly`
   - La session est nettoyée (`session.pop('pending_premium_plan')`)

5. **Redirection Stripe** (`/checkout-redirect`)
   - Création d'une session Stripe Checkout
   - Redirection vers la page de paiement Stripe hébergée
   - URL de succès : `/api/checkout/success?session_id={CHECKOUT_SESSION_ID}`
   - URL d'annulation : `/pricing`

6. **Paiement sur Stripe**
   - L'utilisateur entre ses informations de carte bancaire
   - Stripe traite le paiement
   - En cas de succès : redirection vers `/api/checkout/success`
   - En cas d'annulation : retour sur `/pricing`

7. **Confirmation de paiement** (`/api/checkout/success`)
   - Vérification du statut de paiement via l'API Stripe
   - Mise à jour du plan utilisateur vers Premium
   - Enregistrement des IDs Stripe (`stripe_customer_id`, `stripe_subscription_id`)
   - Création d'une notification de bienvenue
   - **Envoi de l'email de confirmation d'upgrade**
   - **Envoi de la facture par email**
   - Redirection vers le dashboard

### Flux 2 : Upgrade depuis le plan Free (utilisateur connecté)

**Scénario** : L'utilisateur est déjà inscrit avec un plan Free et souhaite passer à Premium.

**Étapes** :

1. **Page de tarification** (`/pricing`)
   - L'utilisateur connecté voit des boutons "Passer à Premium" ou "Passer à Premium Annuel"
   - Au clic, JavaScript appelle `/api/create-checkout-session` avec le plan choisi

2. **Création de session Stripe** (`/api/create-checkout-session`)
   ```javascript
   fetch('/api/create-checkout-session', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({ plan: 'monthly' }) // ou 'yearly'
   })
   ```
   - L'API crée une session Stripe Checkout
   - Retourne l'URL de paiement
   - JavaScript redirige vers cette URL

3. **Paiement et confirmation**
   - Même processus que les étapes 6-7 du Flux 1

### Flux 3 : Webhooks Stripe (paiements récurrents)

**Scénario** : Stripe facture automatiquement les renouvellements mensuels/annuels.

**Webhooks gérés** :

#### 1. `invoice.payment_succeeded`
**Fichier** : `app/routes/api.py` - Fonction `handle_invoice_payment_succeeded()`

```python
def handle_invoice_payment_succeeded(invoice):
    # Récupère l'utilisateur via stripe_customer_id
    # Envoie la facture par email automatiquement
```

**Actions** :
- Envoi automatique de la facture PDF par email
- Email contient : numéro de facture, date, montant dans la devise configurée
- Liens pour télécharger le PDF et voir en ligne

#### 2. `customer.subscription.updated`
**Fichier** : `app/routes/api.py` - Fonction `handle_subscription_updated()`

```python
def handle_subscription_updated(stripe_subscription):
    # Met à jour le plan utilisateur si status = 'active'
    # Envoie email de bienvenue si nouveau Premium
    # Crée une notification
```

**Actions** :
- Mise à jour du plan utilisateur
- Email de bienvenue si première activation
- Notification dans l'interface

#### 3. `customer.subscription.deleted`
**Fichier** : `app/routes/api.py` - Fonction `handle_subscription_deleted()`

```python
def handle_subscription_deleted(stripe_subscription):
    # Rétrograde vers plan Free
    # Envoie email de rétrogradation
    # Crée une notification
```

**Actions** :
- Rétrogradation vers le plan Free
- Email de confirmation
- Notification dans l'interface

#### 4. `invoice.payment_failed`
**Fichier** : `app/routes/api.py` - Fonction `handle_payment_failed()`

```python
def handle_payment_failed(invoice):
    # Crée une notification d'échec de paiement
```

**Actions** :
- Notification d'échec
- L'utilisateur doit mettre à jour ses informations de paiement

### Configuration du webhook dans Stripe

1. Aller dans le Dashboard Stripe → Développeurs → Webhooks
2. Créer un endpoint : `https://votre-domaine.com/api/webhook`
3. Sélectionner les événements :
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copier le secret de signature dans `STRIPE_WEBHOOK_SECRET`

## Gestion des devises

### Devise utilisateur
- Choisie lors de l'inscription
- Stockée dans `users.default_currency`
- Utilisée pour l'affichage des montants

### Devise Stripe
- Les prix Stripe sont configurés en EUR
- La facture affiche toujours la devise réelle de la transaction
- Le montant est converti avec les symboles appropriés (€, $, £, etc.)

## Emails envoyés

### 1. Email de vérification
- Envoyé à l'inscription
- Mentionne l'essai Premium de 7 jours **seulement pour les inscriptions gratuites**
- Ne mentionne **pas** l'essai pour les inscriptions Premium directes

### 2. Email d'upgrade Premium
**Fonction** : `send_plan_upgrade_email(user, plan_name)`
**Quand** : Lors du passage à Premium (paiement initial ou webhook)

Contenu :
- Titre : "🎉 Bienvenue chez Premium !"
- Liste des avantages Premium
- Bouton CTA vers le dashboard

### 3. Email de facture
**Fonction** : `send_invoice_email(user, invoice_id)`
**Quand** : Après chaque paiement réussi

Contenu :
- Numéro de facture
- Date et montant
- Lien téléchargement PDF
- Lien visualisation en ligne

### 4. Email de rétrogradation
**Fonction** : `send_plan_downgrade_email(user, old_plan_name)`
**Quand** : Annulation d'abonnement ou rétrogradation manuelle

Contenu :
- Confirmation de rétrogradation
- Limitations du plan gratuit
- Lien pour repasser à Premium

## Gestion du portail client Stripe

**Route** : `/api/create-portal-session`

Permet aux utilisateurs Premium de :
- Gérer leur abonnement
- Mettre à jour leur carte bancaire
- Voir leurs factures
- Annuler leur abonnement

```javascript
fetch('/api/create-portal-session', { method: 'POST' })
    .then(res => res.json())
    .then(data => window.location.href = data.portal_url)
```

## Notifications dans l'interface

Toutes les actions de paiement créent des notifications dans l'interface :

### Types de notifications
- `upgrade` : Passage à Premium
- `downgrade` : Rétrogradation vers Free
- `payment_failed` : Échec de paiement

**Modèle** : `Notification`
- Affichées dans `/notifications`
- Badge de notification non lue dans le menu
- Marquage comme lu après consultation

## Sécurité

### Vérification des webhooks
```python
stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
```
- Vérifie la signature Stripe
- Empêche les faux webhooks
- Rejette les requêtes non authentifiées

### Métadonnées Stripe
Chaque session Stripe inclut :
```python
metadata = {
    'user_id': current_user.id,
    'plan_type': 'monthly' ou 'yearly'
}
```
- Permet d'identifier l'utilisateur
- Utile pour le support client
- Visible dans le Dashboard Stripe

## Tests recommandés

### 1. Test d'inscription Premium directe
1. Aller sur `/pricing` (non connecté)
2. Cliquer sur "Commencer avec Premium"
3. Remplir le formulaire d'inscription
4. Vérifier : pas de mention d'essai gratuit
5. Se connecter
6. Vérifier : redirection automatique vers Stripe
7. Utiliser une carte de test : `4242 4242 4242 4242`
8. Vérifier : email de bienvenue + facture reçus
9. Vérifier : plan = Premium dans le dashboard

### 2. Test d'upgrade depuis Free
1. Se connecter avec compte Free
2. Aller sur `/pricing`
3. Cliquer sur "Passer à Premium"
4. Compléter le paiement Stripe
5. Vérifier : upgrade réussi, emails reçus

### 3. Test des webhooks
1. Créer un webhook de test dans Stripe
2. Déclencher un événement `invoice.payment_succeeded`
3. Vérifier : facture envoyée par email
4. Déclencher `customer.subscription.deleted`
5. Vérifier : rétrogradation + email

### 4. Test du portail client
1. Se connecter en Premium
2. Aller sur le profil
3. Cliquer sur "Gérer mon abonnement"
4. Vérifier : redirection vers le portail Stripe
5. Tester : annulation d'abonnement
6. Vérifier : rétrogradation + email

## Cartes de test Stripe

```
Paiement réussi : 4242 4242 4242 4242
Paiement refusé : 4000 0000 0000 0002
Authentification requise : 4000 0025 0000 3155
```

Date d'expiration : n'importe quelle date future
CVC : n'importe quel 3 chiffres
Code postal : n'importe quel code

## Erreurs courantes

### Erreur : "Plan Premium non configuré"
**Cause** : `stripe_price_id` non défini dans la table `plans`
**Solution** : Configurer les IDs de prix Stripe

### Erreur : "Invalid signature"
**Cause** : `STRIPE_WEBHOOK_SECRET` incorrect
**Solution** : Vérifier la clé dans le Dashboard Stripe

### Erreur : Session expirée
**Cause** : L'utilisateur a pris trop de temps sur la page Stripe
**Solution** : Réessayer, une nouvelle session sera créée

## Architecture des fichiers

```
app/
├── routes/
│   ├── api.py                  # Routes Stripe et webhooks
│   ├── auth.py                 # Inscription et login
│   └── main.py                 # Dashboard et checkout-redirect
├── utils/
│   └── email.py                # Fonctions d'envoi d'email
├── models.py                   # Modèles User, Plan, Notification
└── templates/
    ├── pricing.html            # Page de tarification
    └── auth/
        └── register.html       # Formulaire d'inscription
```

## Routes importantes

| Route | Méthode | Description |
|-------|---------|-------------|
| `/pricing` | GET | Page de tarification |
| `/auth/register` | POST | Inscription utilisateur |
| `/auth/login` | POST | Connexion (avec redirection Stripe si plan en attente) |
| `/checkout-redirect` | GET | Création session Stripe et redirection |
| `/api/create-checkout-session` | POST | API création session Stripe (pour utilisateurs connectés) |
| `/api/checkout/success` | GET | Confirmation après paiement réussi |
| `/api/create-portal-session` | POST | Accès au portail client Stripe |
| `/api/webhook` | POST | Réception des webhooks Stripe |

## Diagramme de flux simplifié

```
Inscription Premium
├── /pricing (clic "Commencer avec Premium")
├── /auth/register?plan=premium (inscription sans essai gratuit)
├── /auth/login (connexion)
├── /checkout-redirect?plan=monthly (création session Stripe)
├── Stripe Checkout (paiement)
└── /api/checkout/success (confirmation + emails)

Upgrade Free → Premium
├── /pricing (clic "Passer à Premium")
├── JavaScript → /api/create-checkout-session
├── Stripe Checkout (paiement)
└── /api/checkout/success (confirmation + emails)

Renouvellement automatique
├── Stripe facture automatiquement
├── Webhook: invoice.payment_succeeded
└── Email de facture envoyé automatiquement
```

## Support et maintenance

### Logs à surveiller
- Erreurs de création de session Stripe
- Échecs de webhooks
- Échecs d'envoi d'emails

### Métriques à suivre
- Taux de conversion Free → Premium
- Taux d'annulation d'abonnements
- Revenus mensuels récurrents (MRR)
- Taux d'échec de paiement

### Dashboard Stripe
- Vérifier régulièrement les paiements
- Surveiller les webhooks (délais, erreurs)
- Consulter les litiges (disputes)
- Analyser les taux de réussite
