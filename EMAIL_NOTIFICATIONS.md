# Notifications par email pour les changements de plan

## Vue d'ensemble

Le système envoie automatiquement des emails de confirmation à l'utilisateur lors de tout changement de plan (upgrade ou downgrade).

## Fonctions d'email disponibles

### 1. `send_plan_upgrade_email(user, new_plan_name)`

**Utilisée lors du passage à un plan Premium**

**Design de l'email :**
- En-tête gradient violet (Premium)
- Titre : "🎉 Bienvenue chez Premium !"
- Liste des avantages Premium :
  - ✅ Abonnements illimités
  - ✅ Catégories personnalisées illimitées
  - ✅ Services personnalisés illimités
  - ✅ Plans de services illimités
  - ✅ Statistiques avancées
  - ✅ Export de données
  - ✅ Support prioritaire
- Bouton CTA : "Accéder à mon tableau de bord"
- Message de remerciement

**Sujet de l'email :**
`Bienvenue sur {new_plan_name} - Subly Cloud`

**Quand est-il envoyé :**
- Après paiement réussi via Stripe (`/api/checkout/success`)
- Lors de l'activation d'un abonnement via webhook (`handle_subscription_updated`)
- Pour les plans Premium et Premium Annual

### 2. `send_plan_downgrade_email(user, old_plan_name)`

**Utilisée lors de la rétrogradation vers le plan gratuit**

**Design de l'email :**
- En-tête gradient orange (warning)
- Titre : "Rétrogradation confirmée"
- Encadré informatif avec les limitations du plan gratuit :
  - Jusqu'à 5 abonnements
  - Jusqu'à 5 catégories personnalisées
  - Jusqu'à 5 services personnalisés
  - Jusqu'à 10 plans de services personnalisés
  - Statistiques de base
  - Notifications d'échéance
- Rassurance sur conservation des données
- Bouton CTA : "Voir les plans Premium"
- Message d'au revoir positif

**Sujet de l'email :**
`Confirmation de rétrogradation - Subly Cloud`

**Quand est-il envoyé :**
- Lors de la rétrogradation manuelle (`/auth/downgrade-to-free`)
- Lors de l'annulation d'abonnement via webhook (`handle_subscription_deleted`)

## Points d'envoi dans le code

### 1. Rétrogradation manuelle
**Fichier :** `app/routes/auth.py`
**Route :** `/auth/downgrade-to-free`

```python
# Envoyer l'email de confirmation
from app.utils.email import send_plan_downgrade_email
send_plan_downgrade_email(current_user, old_plan_name)
```

### 2. Upgrade via Stripe (paiement réussi)
**Fichier :** `app/routes/api.py`
**Route :** `/api/checkout/success`

```python
# Envoyer l'email de confirmation
from app.utils.email import send_plan_upgrade_email
send_plan_upgrade_email(current_user, premium_plan.name)
```

### 3. Webhook Stripe - Abonnement activé
**Fichier :** `app/routes/api.py`
**Fonction :** `handle_subscription_updated()`

```python
# Envoyer l'email de confirmation uniquement si c'est un nouveau passage à Premium
if not was_premium:
    from app.utils.email import send_plan_upgrade_email
    send_plan_upgrade_email(user, premium_plan.name)
```

### 4. Webhook Stripe - Abonnement annulé
**Fichier :** `app/routes/api.py`
**Fonction :** `handle_subscription_deleted()`

```python
# Envoyer l'email de confirmation de rétrogradation
from app.utils.email import send_plan_downgrade_email
send_plan_downgrade_email(user, old_plan_name)
```

## Gestion des erreurs

Toutes les fonctions d'envoi d'email incluent une gestion d'erreurs :

```python
try:
    mail.send(msg)
    return True
except Exception as e:
    print(f"Erreur lors de l'envoi de l'email : {e}")
    return False
```

En cas d'échec de l'envoi :
- L'erreur est loguée
- **L'action principale (changement de plan) n'est PAS annulée**
- L'utilisateur peut toujours continuer même si l'email n'est pas envoyé

## Format des emails

### Version HTML
- Design responsive
- Gradient de couleur selon le type d'événement
- Boutons CTA stylisés
- Footer avec informations de contact

### Version texte
- Version texte brut pour les clients email ne supportant pas le HTML
- Contient les mêmes informations essentielles
- Liens en texte clair

## Configuration requise

### Variables d'environnement

```env
MAIL_DEFAULT_SENDER=noreply@subly.cloud
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_username
MAIL_PASSWORD=your_password
```

### Flask-Mail

Le système utilise Flask-Mail qui doit être initialisé dans l'application :

```python
from flask_mail import Mail
mail = Mail(app)
```

## Templates des emails

Les templates sont définis directement dans les fonctions Python avec :
- HTML complet avec styles inline
- Version texte brut
- Variables dynamiques (nom utilisateur, plan, URLs)

## Bonnes pratiques

1. **Toujours sauvegarder les données avant d'envoyer l'email**
   ```python
   db.session.commit()  # D'abord
   send_email()         # Ensuite
   ```

2. **Ne pas bloquer l'utilisateur en cas d'échec d'envoi**
   - L'email est informatif, pas critique
   - Ne pas lever d'exception si l'envoi échoue

3. **Personnalisation**
   - Utiliser le prénom si disponible
   - Sinon utiliser l'email
   - Toujours inclure le nom du plan concerné

4. **Éviter les doublons**
   - Pour les webhooks, vérifier si l'email doit être envoyé
   - Ex: Ne pas envoyer d'email d'upgrade si déjà Premium

## Tests recommandés

### Test 1 : Upgrade vers Premium
1. Se connecter avec utilisateur gratuit
2. Passer à Premium via Stripe
3. Vérifier la réception de l'email de bienvenue
4. Vérifier le contenu et les liens

### Test 2 : Rétrogradation manuelle
1. Se connecter avec utilisateur Premium
2. Cliquer sur "Rétrograder vers Gratuit"
3. Confirmer dans la modal
4. Vérifier la réception de l'email de rétrogradation
5. Vérifier que les données sont conservées

### Test 3 : Annulation via Stripe
1. Créer un utilisateur Premium
2. Annuler l'abonnement via le portail Stripe
3. Vérifier que le webhook est reçu
4. Vérifier la réception de l'email de rétrogradation

### Test 4 : Échec d'envoi
1. Configurer une adresse email invalide pour MAIL_SERVER
2. Effectuer un changement de plan
3. Vérifier que le changement de plan fonctionne quand même
4. Vérifier que l'erreur est loguée

## Améliorations futures possibles

- Ajouter des templates Jinja2 séparés pour les emails
- Implémenter un système de queue (Celery) pour l'envoi asynchrone
- Ajouter des emails de rappel avant fin de période d'essai
- Statistiques sur les taux d'ouverture des emails
- A/B testing sur les messages
- Emails de réengagement pour les utilisateurs qui ont rétrogradé
