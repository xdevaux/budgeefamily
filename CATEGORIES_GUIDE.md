# Guide des Catégories Personnalisées

## Vue d'ensemble

Les utilisateurs peuvent maintenant créer et gérer leurs propres catégories personnalisées en plus des catégories par défaut fournies par l'application.

## Fonctionnalités

### Catégories par défaut (globales)
- 10 catégories pré-configurées avec logos, couleurs et icônes
- Disponibles pour tous les utilisateurs
- Non modifiables par les utilisateurs

### Catégories personnalisées
- Chaque utilisateur peut créer ses propres catégories
- Personnalisation complète : nom, description, couleur, icône, logo
- Gestion complète : ajouter, modifier, supprimer, activer/désactiver
- Upload de logos personnalisés (PNG, JPG, GIF, SVG, WebP)

## Utilisation

### Accéder aux catégories
1. Connectez-vous à l'application
2. Cliquez sur "Catégories" dans le menu de navigation

### Créer une catégorie personnalisée

1. Cliquez sur "Créer une catégorie"
2. Remplissez le formulaire :
   - **Nom** : Nom de votre catégorie (ex: "Abonnements Pro")
   - **Description** : Description courte (optionnelle)
   - **Couleur** : Choisissez une couleur avec le sélecteur ou entrez un code hex
   - **Icône** : Classe Font Awesome (ex: `fas fa-briefcase`)
   - **Logo** : Uploadez une image (max 5 MB)
   - **Site web** : URL du site associé (optionnel)
3. Prévisualisez en temps réel
4. Cliquez sur "Créer la catégorie"

### Modifier une catégorie

1. Allez dans "Catégories"
2. Trouvez votre catégorie personnalisée
3. Cliquez sur le bouton "Modifier"
4. Mettez à jour les informations
5. Cliquez sur "Enregistrer les modifications"

### Supprimer une catégorie

1. Allez dans "Catégories"
2. Cliquez sur le bouton "Supprimer" (icône poubelle)
3. Confirmez la suppression

**Note** : Vous ne pouvez pas supprimer une catégorie qui contient des abonnements actifs.

### Activer/Désactiver une catégorie

Cliquez sur le bouton toggle pour activer ou désactiver temporairement une catégorie sans la supprimer.

## Utilisation dans les abonnements

Lorsque vous ajoutez ou modifiez un abonnement, vous pouvez choisir :
- Une catégorie par défaut (globale)
- Une de vos catégories personnalisées
- Aucune catégorie

Les deux types de catégories apparaissent dans le sélecteur.

## Upload de logos

### Formats acceptés
- PNG
- JPG/JPEG
- GIF
- SVG
- WebP

### Taille maximale
5 MB par fichier

### Recommandations
- Utilisez des images carrées pour un meilleur rendu
- Format recommandé : PNG avec fond transparent
- Dimensions recommandées : 200x200 pixels minimum

## Icônes Font Awesome

### Comment trouver une icône
1. Visitez https://fontawesome.com/icons
2. Cherchez une icône
3. Copiez la classe (ex: `fas fa-music`)
4. Collez-la dans le champ "Icône"

### Exemples d'icônes utiles
- `fas fa-briefcase` - Professionnel
- `fas fa-music` - Musique
- `fas fa-film` - Vidéo
- `fas fa-gamepad` - Jeux
- `fas fa-heartbeat` - Santé
- `fas fa-book` - Éducation
- `fas fa-car` - Transport
- `fas fa-home` - Maison

## Codes couleur

### Couleurs prédéfinies
- `#E50914` - Rouge (Netflix style)
- `#1DB954` - Vert (Spotify style)
- `#4285F4` - Bleu (Google style)
- `#FF6900` - Orange
- `#6366F1` - Violet
- `#00C851` - Vert clair
- `#FF0080` - Rose

### Créer votre propre couleur
Utilisez le sélecteur de couleur ou entrez un code hexadécimal (ex: `#FF5733`)

## Limitations

- **Plan gratuit** : Nombre illimité de catégories personnalisées
- **Nom unique** : Vous ne pouvez pas avoir deux catégories avec le même nom
- **Suppression** : Impossible si des abonnements utilisent cette catégorie

## Conseils d'utilisation

### Organisation
- Créez des catégories par domaine (Pro, Perso, Famille)
- Ou par type de service (Streaming, Cloud, Outils)
- Utilisez des couleurs cohérentes pour faciliter l'identification

### Logos
- Téléchargez les logos officiels des services depuis leurs sites web
- Ou créez vos propres logos avec des outils de design

### Maintenance
- Désactivez les catégories temporairement non utilisées
- Nettoyez régulièrement les catégories obsolètes

## Architecture technique

### Base de données
- **Table** : `categories`
- **Champ clé** : `user_id` (NULL = catégorie globale, INT = catégorie personnalisée)
- Les catégories globales ont `user_id = NULL`
- Les catégories personnalisées ont `user_id = ID de l'utilisateur`

### Modèle
```python
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)  # NULL = globale
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    logo_url = db.Column(db.String(500), nullable=True)
    website_url = db.Column(db.String(500), nullable=True)
    color = db.Column(db.String(7), default='#6c757d')
    icon = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
```

### Routes
- `GET/POST /categories/add` - Créer une catégorie
- `GET/POST /categories/<id>/edit` - Modifier une catégorie
- `POST /categories/<id>/delete` - Supprimer une catégorie
- `POST /categories/<id>/toggle` - Activer/Désactiver une catégorie

## Dépannage

### "Vous avez déjà une catégorie nommée X"
Changez le nom de votre catégorie car vous en avez déjà une avec ce nom.

### "Impossible de supprimer cette catégorie"
Des abonnements utilisent cette catégorie. Changez d'abord la catégorie de ces abonnements.

### Le logo ne s'affiche pas
- Vérifiez que le fichier est au bon format (PNG, JPG, etc.)
- Vérifiez que la taille ne dépasse pas 5 MB
- Essayez un autre fichier

### L'icône ne s'affiche pas
- Vérifiez que vous avez utilisé la bonne classe Font Awesome
- Assurez-vous d'inclure le préfixe `fas`, `far`, ou `fab`
- Exemple correct : `fas fa-music`

## Support

Pour toute question ou problème, consultez la documentation générale ou créez une issue sur GitHub.

---

Mise à jour : 30 Décembre 2025
