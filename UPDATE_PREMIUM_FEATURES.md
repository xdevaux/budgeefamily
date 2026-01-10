# Mise à jour des fonctionnalités Premium

## Changement effectué

Les catégories personnalisées sont maintenant **exclusives au plan Premium**.

## Pour appliquer les changements

### Si vous utilisez une base de données existante

Exécutez cette commande SQL pour mettre à jour les fonctionnalités du plan Premium :

```sql
UPDATE plans
SET features = '["Abonnements illimités", "Catégories personnalisées (logos, couleurs, icônes)", "Accès aux catégories par défaut", "Statistiques avancées", "Notifications personnalisables", "Support prioritaire", "Export des données (PDF, CSV)", "Accès anticipé aux nouvelles fonctionnalités"]'::json,
    description = 'Plan Premium avec abonnements illimités et catégories personnalisées'
WHERE name = 'Premium';
```

### Si vous créez une nouvelle base de données

Supprimez et recréez la base de données :

```bash
# Supprimer les tables (ATTENTION: perte de données)
psql -U xavierdx -d subly_app -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Réinitialiser
python init_db.py
```

## Vérification

Pour vérifier que la mise à jour a fonctionné :

```sql
SELECT name, description, features FROM plans WHERE name = 'Premium';
```

---

Date : 30 Décembre 2025
