from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per day", "200 per hour"],
    storage_uri="memory://"
)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'info'
    mail.init_app(app)
    limiter.init_app(app)

    from app.routes import auth, main, subscriptions, api, categories, services, admin, exports, credits, credit_types, revenues, employers, banks, installments, checkbooks, card_purchases
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(subscriptions.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(categories.bp)
    app.register_blueprint(services.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(exports.bp)
    app.register_blueprint(credits.bp)
    app.register_blueprint(credit_types.bp)
    app.register_blueprint(revenues.bp)
    app.register_blueprint(employers.bp)
    app.register_blueprint(banks.bp)
    app.register_blueprint(installments.bp)
    app.register_blueprint(checkbooks.bp)
    app.register_blueprint(card_purchases.bp)

    # Ajouter datetime dans le contexte Jinja2
    from datetime import datetime
    import pytz
    from flask_login import current_user
    import random

    # Phrases d'accueil aléatoires positives
    WELCOME_MESSAGES = [
        "Ravi de vous revoir !",
        "Excellente journée pour optimiser vos abonnements !",
        "Votre budget est entre de bonnes mains !",
        "Continuez comme ça, vous gérez parfaitement !",
        "Bravo pour votre gestion financière !",
        "Un nouveau jour, de nouvelles économies !",
        "Vous êtes sur la bonne voie !",
        "Gardez le contrôle de vos abonnements !",
        "Vous faites un travail formidable !",
        "Chaque jour est une opportunité d'économiser !",
        "Votre organisation est exemplaire !",
        "Restez maître de votre budget !",
        "Bienvenue dans votre espace !",
        "Prêt à gérer efficacement vos abonnements ?",
        "Votre succès financier commence ici !",
    ]

    @app.context_processor
    def inject_now():
        # Utiliser le timezone de l'utilisateur s'il est connecté, sinon Europe/Paris
        if current_user.is_authenticated and current_user.timezone:
            tz = pytz.timezone(current_user.timezone)
        else:
            tz = pytz.timezone(app.config.get('TIMEZONE', 'Europe/Paris'))

        # Ajouter un message d'accueil aléatoire
        welcome_message = random.choice(WELCOME_MESSAGES)

        return {
            'now': datetime.now(tz),
            'current_year': datetime.now(tz).year,
            'welcome_message': welcome_message
        }

    # Filtres Jinja2 personnalisés
    @app.template_filter('translate_cycle')
    def translate_cycle(cycle):
        """Traduit les cycles de facturation en français"""
        translations = {
            'monthly': 'Mensuel',
            'yearly': 'Annuel',
            'weekly': 'Hebdomadaire',
            'quarterly': 'Trimestriel'
        }
        return translations.get(cycle, cycle)

    @app.template_filter('currency_symbol')
    def currency_symbol(currency_code):
        """Convertit les codes de devise en symboles"""
        symbols = {
            'EUR': '€',
            'USD': '$',
            'GBP': '£'
        }
        return symbols.get(currency_code, currency_code)

    @app.template_filter('format_amount')
    def format_amount(amount):
        """Formate un montant au format français (virgule pour décimales, espace pour milliers)"""
        try:
            value = float(amount)
            # Formater avec 2 décimales
            formatted = f"{value:,.2f}"
            # Remplacer le séparateur de milliers par un espace
            formatted = formatted.replace(',', ' ')
            # Remplacer le point décimal par une virgule
            formatted = formatted.replace('.', ',')
            return formatted
        except (ValueError, TypeError):
            return "0,00"

    @app.template_filter('to_user_time')
    def to_user_time(dt):
        """Convertit une datetime UTC dans le fuseau horaire de l'utilisateur"""
        if dt is None:
            return None
        # Utiliser le timezone de l'utilisateur s'il est connecté, sinon Europe/Paris
        if current_user.is_authenticated and current_user.timezone:
            tz = pytz.timezone(current_user.timezone)
        else:
            tz = pytz.timezone(app.config.get('TIMEZONE', 'Europe/Paris'))

        if dt.tzinfo is None:
            # Si la date n'a pas de timezone, on considère qu'elle est en UTC
            dt = pytz.utc.localize(dt)
        return dt.astimezone(tz)

    @app.template_filter('format_datetime')
    def format_datetime(dt, format='%d/%m/%Y %H:%M'):
        """Formate une datetime dans le fuseau horaire de l'utilisateur"""
        if dt is None:
            return ''
        dt_user = to_user_time(dt)
        return dt_user.strftime(format)

    # Garder l'ancien filtre pour compatibilité
    app.template_filter('to_paris_time')(to_user_time)

    # Enregistrer les commandes CLI
    from app import commands
    commands.init_app(app)

    return app


from app import models
