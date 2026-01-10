# Guide de déploiement - Subly Cloud

Ce guide explique comment déployer Subly Cloud en production.

## Options de déploiement

### 1. Déploiement avec Gunicorn (serveur Linux)

#### Installation

```bash
pip install -r requirements-prod.txt
```

#### Lancement

```bash
gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
```

Options :
- `-w 4` : 4 workers (processus)
- `-b 0.0.0.0:8000` : Écouter sur le port 8000

#### Configuration avec systemd

Créez `/etc/systemd/system/subly-cloud.service` :

```ini
[Unit]
Description=Subly Cloud Application
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/app.subly.cloud
Environment="PATH=/var/www/app.subly.cloud/.venv/bin"
ExecStart=/var/www/app.subly.cloud/.venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 wsgi:app

[Install]
WantedBy=multi-user.target
```

Activez et démarrez :
```bash
sudo systemctl enable subly-cloud
sudo systemctl start subly-cloud
sudo systemctl status subly-cloud
```

### 2. Configuration Nginx (reverse proxy)

Créez `/etc/nginx/sites-available/subly.cloud` :

```nginx
server {
    listen 80;
    server_name subly.cloud www.subly.cloud;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/app.subly.cloud/app/static;
        expires 30d;
    }
}
```

Activez le site :
```bash
sudo ln -s /etc/nginx/sites-available/subly.cloud /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. SSL avec Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d subly.cloud -d www.subly.cloud
```

### 4. Variables d'environnement en production

Créez un fichier `.env` en production :

```env
DATABASE_URL=postgresql://user:password@localhost/subly_app
SECRET_KEY=VOTRE-CLÉ-SECRÈTE-TRÈS-LONGUE-ET-ALÉATOIRE
FLASK_ENV=production

STRIPE_PUBLIC_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

**Important** : Générez une clé secrète forte :
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Base de données en production

#### Backup automatique

Créez `/usr/local/bin/backup-subly.sh` :

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/subly-cloud"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

pg_dump subly_app > $BACKUP_DIR/subly_app_$DATE.sql

# Garder seulement les 7 derniers backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
```

Ajoutez une tâche cron :
```bash
0 2 * * * /usr/local/bin/backup-subly.sh
```

### 6. Monitoring

#### Logs

Consultez les logs de l'application :
```bash
sudo journalctl -u subly-cloud -f
```

#### Monitoring avec Supervisor

Alternative à systemd, installez Supervisor :

```bash
sudo apt install supervisor
```

Créez `/etc/supervisor/conf.d/subly-cloud.conf` :

```ini
[program:subly-cloud]
command=/var/www/app.subly.cloud/.venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 wsgi:app
directory=/var/www/app.subly.cloud
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/subly-cloud.log
```

### 7. Déploiement sur des plateformes cloud

#### Heroku

1. Créez un fichier `Procfile` :
   ```
   web: gunicorn wsgi:app
   ```

2. Déployez :
   ```bash
   heroku create subly-cloud
   heroku addons:create heroku-postgresql:hobby-dev
   git push heroku main
   heroku run python init_db.py
   ```

#### DigitalOcean App Platform

1. Connectez votre repo GitHub
2. Configurez :
   - Build command: `pip install -r requirements-prod.txt`
   - Run command: `gunicorn wsgi:app`
3. Ajoutez une base PostgreSQL
4. Configurez les variables d'environnement

#### Railway

1. Connectez votre repo
2. Ajoutez PostgreSQL
3. Variables d'environnement sont automatiques
4. Deploy automatique

### 8. Optimisations de performance

#### Cache Redis (optionnel)

Ajoutez à `requirements-prod.txt` :
```
redis==5.0.1
flask-caching==2.1.0
```

Configuration dans `config.py` :
```python
CACHE_TYPE = 'redis'
CACHE_REDIS_URL = os.environ.get('REDIS_URL')
```

#### CDN pour les assets statiques

Utilisez un CDN comme Cloudflare pour servir les fichiers statiques.

### 9. Sécurité

- [ ] Utilisez HTTPS obligatoire
- [ ] Mettez à jour régulièrement les dépendances
- [ ] Configurez les CORS si nécessaire
- [ ] Activez le rate limiting
- [ ] Configurez les backups automatiques
- [ ] Monitorer les logs d'erreur
- [ ] Utilisez des clés Stripe en mode production (live)

### 10. Checklist de déploiement

- [ ] Variables d'environnement configurées
- [ ] Base de données créée et migrée
- [ ] Secret key généré et sécurisé
- [ ] Stripe configuré en mode production
- [ ] OAuth callbacks mis à jour avec le domaine de production
- [ ] SSL/HTTPS activé
- [ ] Backups automatiques configurés
- [ ] Monitoring en place
- [ ] Logs configurés

## Support

Pour toute question sur le déploiement, consultez la documentation ou contactez le support.
