from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from flask_babel import Babel, gettext, lazy_gettext
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
babel = Babel()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per day", "200 per hour"],
    storage_uri="memory://"
)


def get_locale():
    """Détermine la langue à utiliser pour la requête actuelle"""
    from flask_login import current_user

    # 1. Si l'utilisateur est connecté et a une préférence de langue
    if current_user.is_authenticated and hasattr(current_user, 'language') and current_user.language:
        return current_user.language

    # 2. Si une langue est définie en session (pour les non-connectés)
    if 'language' in session:
        return session['language']

    # 3. Détecter la langue du navigateur
    return request.accept_languages.best_match(['fr', 'en']) or 'fr'


def get_timezone():
    """Détermine le fuseau horaire à utiliser pour la requête actuelle"""
    from flask_login import current_user
    import pytz

    # Si l'utilisateur est connecté et a un timezone défini
    if current_user.is_authenticated and hasattr(current_user, 'timezone') and current_user.timezone:
        return current_user.timezone

    # Sinon, utiliser le timezone par défaut
    return 'Europe/Paris'


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
    babel.init_app(app, locale_selector=get_locale, timezone_selector=get_timezone)
    limiter.init_app(app)

    from app.routes import auth, main, subscriptions, api, categories, services, admin, exports, credits, credit_types, revenues, employers, banks, installments, checkbooks, card_purchases, card_purchase_categories, reminders, providers
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
    app.register_blueprint(card_purchase_categories.bp)
    app.register_blueprint(reminders.bp)
    app.register_blueprint(providers.bp)

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
            'welcome_message': welcome_message,
            'get_locale': get_locale,
            '_': gettext
        }

    # Filtres Jinja2 personnalisés
    @app.template_filter('translate_cycle')
    def translate_cycle(cycle):
        """Traduit les cycles de facturation"""
        from flask_babel import gettext as _
        translations = {
            'monthly': _('Mensuel'),
            'yearly': _('Annuel'),
            'weekly': _('Hebdomadaire'),
            'quarterly': _('Trimestriel')
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

    @app.template_filter('translate_month')
    def translate_month(month_number):
        """Traduit le numéro du mois en nom abrégé"""
        from flask_babel import gettext as _
        months = {
            1: _('Janv.'),
            2: _('Fév.'),
            3: _('Mars'),
            4: _('Avr.'),
            5: _('Mai'),
            6: _('Juin'),
            7: _('Juil.'),
            8: _('Août'),
            9: _('Sept.'),
            10: _('Oct.'),
            11: _('Nov.'),
            12: _('Déc.')
        }
        return months.get(month_number, '')

    @app.template_filter('get_translated_description')
    def get_translated_description(obj):
        """Retourne la description traduite pour un objet Category ou Service"""
        if obj and hasattr(obj, 'get_description'):
            return obj.get_description(locale=get_locale())
        return obj.description if obj and hasattr(obj, 'description') else ''

    @app.template_filter('translate_category')
    def translate_category(category_name):
        """Traduit les noms et descriptions des catégories par défaut"""
        from flask_babel import gettext as _
        translations = {
            # Noms de catégories
            'Alimentation': _('Alimentation'),
            'Carburant': _('Carburant'),
            'Habillement': _('Habillement'),
            'Restaurant': _('Restaurant'),
            'Transport': _('Transport'),
            'Santé & Pharmacie': _('Santé & Pharmacie'),
            'Loisirs & Culture': _('Loisirs & Culture'),
            'Maison & Jardin': _('Maison & Jardin'),
            'Électronique & High-tech': _('Électronique & High-tech'),
            'Sport & Fitness': _('Sport & Fitness'),
            'Beauté & Cosmétiques': _('Beauté & Cosmétiques'),
            'Éducation & Formation': _('Éducation & Formation'),
            'Voyages & Hébergement': _('Voyages & Hébergement'),
            'Cadeaux': _('Cadeaux'),
            'Animaux': _('Animaux'),
            'Autre': _('Autre'),
            # Descriptions de catégories
            'Courses alimentaires, supermarché': _('Courses alimentaires, supermarché'),
            'Essence, diesel, station-service': _('Essence, diesel, station-service'),
            'Vêtements, chaussures, accessoires': _('Vêtements, chaussures, accessoires'),
            'Restaurants, fast-food, livraison': _('Restaurants, fast-food, livraison'),
            'Transports en commun, taxi, parking': _('Transports en commun, taxi, parking'),
            'Médicaments, pharmacie, soins': _('Médicaments, pharmacie, soins'),
            'Cinéma, concerts, musées, spectacles': _('Cinéma, concerts, musées, spectacles'),
            'Bricolage, jardinage, décoration': _('Bricolage, jardinage, décoration'),
            'Informatique, électronique, gadgets': _('Informatique, électronique, gadgets'),
            'Équipement sportif, salle de sport': _('Équipement sportif, salle de sport'),
            'Coiffeur, esthétique, cosmétiques': _('Coiffeur, esthétique, cosmétiques'),
            'Livres, formations, cours': _('Livres, formations, cours'),
            'Hôtels, voyages, locations': _('Hôtels, voyages, locations'),
            'Cadeaux pour occasions spéciales': _('Cadeaux pour occasions spéciales'),
            'Nourriture et soins pour animaux': _('Nourriture et soins pour animaux'),
            'Dépenses diverses non catégorisées': _('Dépenses diverses non catégorisées')
        }
        return translations.get(category_name, category_name)

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

    @app.template_filter('format_user_datetime')
    def format_user_datetime(dt, user, format='%d/%m/%Y %H:%M'):
        """Formate une datetime dans le fuseau horaire d'un utilisateur spécifique"""
        if dt is None:
            return ''
        # Utiliser le timezone de l'utilisateur passé en paramètre
        if user and user.timezone:
            tz = pytz.timezone(user.timezone)
        else:
            tz = pytz.timezone(app.config.get('TIMEZONE', 'Europe/Paris'))

        if dt.tzinfo is None:
            # Si la date n'a pas de timezone, on considère qu'elle est en UTC
            dt = pytz.utc.localize(dt)
        dt_user = dt.astimezone(tz)
        return dt_user.strftime(format)

    # Garder l'ancien filtre pour compatibilité
    app.template_filter('to_paris_time')(to_user_time)

    # Enregistrer les commandes CLI
    from app import commands
    commands.init_app(app)

    return app


from app import models
