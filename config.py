import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://localhost/budgeefamily_app'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Stripe
    STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')

    # OAuth Google
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

    # OAuth Apple
    APPLE_CLIENT_ID = os.environ.get('APPLE_CLIENT_ID')
    APPLE_CLIENT_SECRET = os.environ.get('APPLE_CLIENT_SECRET')

    # Flask-Mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'false').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@budgeefamily.com')

    # Configuration pour les URLs en dehors des requêtes HTTP (pour les emails via cron)
    SERVER_NAME = os.environ.get('SERVER_NAME', 'budgeefamily.com')
    PREFERRED_URL_SCHEME = os.environ.get('PREFERRED_URL_SCHEME', 'https')
    APPLICATION_ROOT = os.environ.get('APPLICATION_ROOT', '/')

    # Limites d'abonnements
    FREE_SUBSCRIPTION_LIMIT = 5

    # Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max pour les documents
    UPLOAD_FOLDER = os.path.join(basedir, 'app/static/uploads')

    # Timezone
    TIMEZONE = 'Europe/Paris'
