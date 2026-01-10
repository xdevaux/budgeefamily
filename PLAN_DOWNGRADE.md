# Système de rétrogradation de plan

## Fonctionnement

Le système permet aux utilisateurs Premium de rétrograder immédiatement vers le plan gratuit depuis leur profil.

## Architecture

### Route disponible

#### `/auth/downgrade-to-free` (POST)
Rétrograde immédiatement l'utilisateur vers le plan gratuit.

**Comportement :**
- Vérifie que l'utilisateur a un plan Premium
- Récupère le plan gratuit depuis la base de données
- Change le plan de l'utilisateur immédiatement
- Affiche un message de confirmation
- L'effet est **instantané**

**Restrictions :**
- Impossible si l'utilisateur est déjà sur le plan gratuit

## Interface utilisateur (Profil)

### Affichage pour utilisateur Premium

```
┌─────────────────────────────────────────────┐
│ Plan actuel                                 │
├─────────────────────────────────────────────┤
│ Plan Premium                    [Rétrograder]│
│ X / illimité abonnements actifs             │
│                                             │
│ ℹ️ Bon à savoir : Vous pouvez rétrograder │
│   vers le plan gratuit à tout moment.      │
│   La rétrogradation est immédiate.         │
└─────────────────────────────────────────────┘
```

### Affichage pour utilisateur gratuit

```
┌─────────────────────────────────────────────┐
│ Plan actuel                                 │
├─────────────────────────────────────────────┤
│ Plan Free                 [Passer à Premium]│
│ X / 5 abonnements actifs                    │
└─────────────────────────────────────────────┘
```

### Modal de confirmation

Lors du clic sur "Rétrograder vers Gratuit", une modal s'affiche avec :

**En-tête warning (jaune) :**
- Titre : "Confirmer la rétrogradation"

**Corps du message :**
- Question de confirmation
- Alerte warning avec les limitations :
  - **Rétrogradation immédiate** - L'effet est instantané
  - Limite d'abonnements : **5 maximum** (contre illimité)
  - Catégories personnalisées : **5 maximum** (contre illimité)
  - Services personnalisés : **5 maximum** (contre illimité)
  - Plans personnalisés : **10 maximum** (contre illimité)
- Alerte success : Possibilité de repasser à Premium à tout moment

**Boutons :**
- "Annuler" (secondaire) - Ferme la modal
- "Rétrograder maintenant" (warning/jaune) - Confirme l'action

## Flux utilisateur

### Scénario : Rétrogradation simple

1. Utilisateur Premium va sur son profil
2. Clique sur "Rétrograder vers Gratuit"
3. Lit les explications dans la modal
4. Clique sur "Rétrograder maintenant"
5. → Rétrogradation instantanée vers le plan Free
6. Message de confirmation affiché
7. Les limitations du plan gratuit s'appliquent immédiatement

### Scénario : Changement d'avis

1. Utilisateur clique sur "Rétrograder vers Gratuit"
2. Lit la modal
3. Change d'avis
4. Clique sur "Annuler"
5. → Aucun changement, garde son plan Premium

### Scénario : Repassage à Premium

1. Utilisateur sur plan gratuit
2. Clique sur "Passer à Premium"
3. Accède à la page de tarification
4. Sélectionne un plan Premium
5. → Récupère tous les avantages Premium

## Limitations du plan gratuit

Après rétrogradation, l'utilisateur a :
- **5 abonnements maximum** (au lieu d'illimité)
- **5 catégories personnalisées maximum** (au lieu d'illimité)
- **5 services personnalisés maximum** (au lieu d'illimité)
- **10 plans personnalisés maximum** (au lieu d'illimité)

Si l'utilisateur dépasse ces limites au moment de la rétrogradation :
- Il ne pourra pas créer de nouveaux éléments
- Mais les éléments existants restent accessibles
- Il devra supprimer des éléments pour en créer de nouveaux

## Avantages de cette approche

✅ **Simple et direct**
- Un seul clic pour rétrograder
- Effet immédiat, pas d'ambiguïté

✅ **Transparent pour l'utilisateur**
- Toutes les limitations sont affichées clairement
- L'utilisateur sait exactement ce qui va se passer

✅ **Réversible**
- L'utilisateur peut repasser à Premium à tout moment
- Lien direct vers la page de tarification

✅ **Pas de complexité technique**
- Pas de cron job
- Pas de gestion de dates d'expiration
- Code simple et maintenable

## Base de données

### Modèle User

Le champ `plan_id` pointe vers le plan actuel de l'utilisateur :
- Premium → `plan_id` pointe vers un plan Premium
- Après rétrogradation → `plan_id` pointe vers le plan Free

### Migration

Migration appliquée : `a4784daf5997_remove_plan_cancellation_fields_for_immediate_downgrade.py`

Champs supprimés :
- `users.plan_cancel_at_period_end`
- `users.plan_period_end_date`

Ces champs étaient utilisés pour un système d'annulation différée qui a été simplifié.

## Tests recommandés

1. **Test de rétrogradation :**
   - Se connecter avec un utilisateur Premium
   - Cliquer sur "Rétrograder vers Gratuit"
   - Vérifier que la modal s'affiche correctement
   - Confirmer la rétrogradation
   - Vérifier que le plan passe bien à Free
   - Vérifier que les limitations s'appliquent

2. **Test d'annulation de rétrogradation :**
   - Cliquer sur "Rétrograder vers Gratuit"
   - Cliquer sur "Annuler" dans la modal
   - Vérifier que le plan reste Premium

3. **Test de repassage à Premium :**
   - Partir d'un utilisateur gratuit
   - Cliquer sur "Passer à Premium"
   - Vérifier la redirection vers la page de tarification

4. **Test avec utilisateur déjà gratuit :**
   - Se connecter avec un utilisateur Free
   - Vérifier qu'il n'y a pas de bouton "Rétrograder"
   - Vérifier qu'il y a bien le bouton "Passer à Premium"

## Code source

### Route (app/routes/auth.py)

```python
@bp.route('/downgrade-to-free', methods=['POST'])
@login_required
def downgrade_to_free():
    """Rétrograde immédiatement l'utilisateur vers le plan gratuit"""
    if not current_user.plan or current_user.plan.name == 'Free':
        flash('Vous êtes déjà sur le plan gratuit.', 'info')
        return redirect(url_for('auth.profile'))

    free_plan = Plan.query.filter_by(name='Free').first()
    if not free_plan:
        flash('Erreur: Le plan gratuit n\'existe pas.', 'danger')
        return redirect(url_for('auth.profile'))

    old_plan_name = current_user.plan.name
    current_user.plan = free_plan
    db.session.commit()

    flash(f'Vous avez été rétrogradé du plan {old_plan_name} vers le plan gratuit avec succès.', 'success')
    return redirect(url_for('auth.profile'))
```

### Template (app/templates/auth/profile.html)

Le bouton s'affiche uniquement pour les utilisateurs Premium :

```jinja2
{% if current_user.plan.name == 'Free' %}
    <a href="{{ url_for('main.pricing') }}" class="btn btn-primary">
        <i class="fas fa-arrow-up"></i> Passer à Premium
    </a>
{% else %}
    <button type="button" class="btn btn-outline-danger btn-sm"
            data-bs-toggle="modal" data-bs-target="#downgradePlanModal">
        <i class="fas fa-arrow-down"></i> Rétrograder vers Gratuit
    </button>
{% endif %}
```

## Notes importantes

### Pas de fermeture de compte

L'utilisateur ne peut **pas fermer son compte** :
- Il peut seulement rétrograder vers le plan gratuit
- Le compte reste actif
- Toutes les données sont conservées

### Données conservées

Lors de la rétrogradation, **toutes les données sont conservées** :
- Abonnements existants
- Catégories personnalisées
- Services personnalisés
- Plans personnalisés
- Historique

L'utilisateur ne perd rien, il ne peut simplement plus créer de nouveaux éléments s'il dépasse les limites du plan gratuit.

## Améliorations futures possibles

- Ajouter une option de feedback lors de la rétrogradation
- Afficher un récapitulatif des éléments qui seront affectés
- Envoyer un email de confirmation après rétrogradation
- Proposer une enquête de satisfaction
- Ajouter des statistiques de rétrogradation dans l'admin
