# Catégories Personnalisées - Fonctionnalité Premium

## Résumé des changements

Les catégories personnalisées sont maintenant **exclusives au plan Premium**. Seuls les utilisateurs avec un abonnement Premium peuvent créer, modifier, supprimer et activer/désactiver leurs propres catégories.

## Modifications apportées

### 1. Modèle User (`app/models.py`)
Ajout de deux nouvelles méthodes :
- `is_premium()` - Vérifie si l'utilisateur a le plan Premium
- `can_create_custom_category()` - Vérifie si l'utilisateur peut créer des catégories personnalisées

### 2. Routes Catégories (`app/routes/categories.py`)
Toutes les routes de gestion des catégories personnalisées ont été protégées :
- `POST /categories/add` - Vérification Premium requise
- `GET/POST /categories/<id>/edit` - Vérification Premium requise
- `POST /categories/<id>/delete` - Vérification Premium requise
- `POST /categories/<id>/toggle` - Vérification Premium requise

Si un utilisateur gratuit tente d'accéder à ces fonctionnalités, il est redirigé vers la page de tarification avec un message approprié.

### 3. Template Catégories (`app/templates/categories/list.html`)

**Pour les utilisateurs gratuits** :
- ✅ Bouton "Créer une catégorie" remplacé par "Passer à Premium pour créer vos catégories"
- ✅ Message promotionnel expliquant les avantages du plan Premium
- ✅ Boutons d'action (modifier, activer/désactiver, supprimer) remplacés par un message de verrouillage

**Pour les utilisateurs Premium** :
- ✅ Bouton "Créer une catégorie" visible
- ✅ Tous les boutons d'action visibles et fonctionnels

### 4. Page de tarification (`app/templates/pricing.html`)
Mise à jour de la liste des fonctionnalités Premium :
- **Nouvelle ligne** : "Catégories personnalisées (logos, couleurs, icônes)"
- Clarification : "Accès aux catégories par défaut" (disponible pour tous)

### 5. Script d'initialisation (`init_db.py`)
Mise à jour de la description et des fonctionnalités du plan Premium pour inclure les catégories personnalisées.

## Comportement

### Utilisateur Gratuit (Plan Free)

**Ce qu'il peut faire** :
- ✅ Voir toutes les catégories par défaut (globales)
- ✅ Utiliser les catégories par défaut dans ses abonnements
- ✅ Voir ses anciennes catégories personnalisées (s'il en a créé avant de rétrograder)

**Ce qu'il ne peut PAS faire** :
- ❌ Créer de nouvelles catégories personnalisées
- ❌ Modifier ses catégories personnalisées existantes
- ❌ Supprimer ses catégories personnalisées
- ❌ Activer/désactiver ses catégories personnalisées

**Messages affichés** :
- Bandeau promotionnel : "Créez vos propres catégories avec Premium"
- Bouton en haut : "Passer à Premium pour créer vos catégories"
- Sur catégories existantes : "Plan Premium requis pour gérer cette catégorie"

### Utilisateur Premium

**Ce qu'il peut faire** :
- ✅ Créer des catégories personnalisées illimitées
- ✅ Modifier toutes ses catégories personnalisées
- ✅ Supprimer ses catégories personnalisées
- ✅ Activer/désactiver ses catégories personnalisées
- ✅ Uploader des logos personnalisés
- ✅ Choisir couleurs et icônes
- ✅ Utiliser les catégories par défaut

## Cas d'usage

### Scénario 1 : Utilisateur gratuit découvre les catégories
1. Va dans "Catégories"
2. Voit les 10 catégories par défaut
3. Voit un message promotionnel pour Premium
4. Clic sur "Passer à Premium" → Redirigé vers la page de tarification

### Scénario 2 : Utilisateur gratuit tente de créer une catégorie
1. Clic sur "Passer à Premium pour créer vos catégories"
2. Redirigé vers la page de tarification
3. Peut souscrire au plan Premium

### Scénario 3 : Utilisateur Premium crée une catégorie
1. Va dans "Catégories"
2. Clic sur "Créer une catégorie"
3. Remplit le formulaire avec logo, couleur, icône
4. Catégorie créée avec succès
5. Disponible dans le sélecteur lors de l'ajout d'abonnements

### Scénario 4 : Utilisateur Premium rétrograde vers Free
1. A 5 catégories personnalisées créées
2. Rétrograde vers le plan Free
3. Ses catégories personnalisées restent visibles mais **verrouillées**
4. Message affiché : "Plan Premium requis pour gérer cette catégorie"
5. Peut toujours utiliser ces catégories dans ses abonnements existants
6. Ne peut plus les modifier, supprimer ou en créer de nouvelles

## Avantages de cette approche

### Pour l'utilisateur gratuit
- ✅ Découvre la valeur du plan Premium
- ✅ Garde l'accès aux catégories par défaut (10 catégories)
- ✅ Comprend clairement ce qu'il débloque avec Premium

### Pour l'utilisateur Premium
- ✅ Fonctionnalité exclusive valorisée
- ✅ Personnalisation complète de l'organisation
- ✅ Expérience utilisateur enrichie

### Pour le business
- ✅ Incitation claire à passer à Premium
- ✅ Différenciation nette entre les plans
- ✅ Valorisation de l'abonnement Premium

## Tests recommandés

1. **Compte gratuit** :
   - ✓ Vérifier qu'on ne peut pas créer de catégorie
   - ✓ Vérifier la redirection vers la page de tarification
   - ✓ Vérifier les messages promotionnels

2. **Compte Premium** :
   - ✓ Créer une catégorie personnalisée
   - ✓ Modifier une catégorie
   - ✓ Supprimer une catégorie
   - ✓ Activer/désactiver une catégorie

3. **Rétrogradation** :
   - ✓ Créer des catégories en Premium
   - ✓ Rétrograder vers Free
   - ✓ Vérifier que les catégories sont verrouillées mais visibles

## Migration des données existantes

Si vous avez des utilisateurs avec des catégories personnalisées créées avant cette mise à jour :
- Leurs catégories restent fonctionnelles
- S'ils sont gratuits, elles deviennent verrouillées
- S'ils sont Premium, tout continue de fonctionner normalement

Aucune perte de données.

## Documentation utilisateur

Ajoutez cette information dans votre documentation :

> **Catégories Personnalisées - Fonctionnalité Premium**
>
> Avec le plan Premium, créez vos propres catégories d'abonnements avec :
> - Logos personnalisés
> - Couleurs sur mesure
> - Icônes Font Awesome
> - Liens vers sites web
>
> Le plan gratuit donne accès aux 10 catégories par défaut.

---

Mise à jour : 30 Décembre 2025
