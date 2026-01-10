from datetime import datetime, timedelta
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets


# Tables d'association pour les éléments masqués
hidden_categories = db.Table('hidden_categories',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id'), primary_key=True)
)

hidden_services = db.Table('hidden_services',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('service_id', db.Integer, db.ForeignKey('services.id'), primary_key=True)
)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)

    # OAuth
    oauth_provider = db.Column(db.String(20), nullable=True)  # 'google', 'apple', None
    oauth_id = db.Column(db.String(200), nullable=True)

    # Profile
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    default_currency = db.Column(db.String(3), default='EUR')  # Devise par défaut
    country = db.Column(db.String(2), nullable=True)  # Code pays ISO 3166-1 alpha-2 (FR, US, etc.)
    timezone = db.Column(db.String(50), default='Europe/Paris')  # Fuseau horaire de l'utilisateur

    # Subscription plan
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=True)
    plan = db.relationship('Plan', back_populates='users')

    # Stripe
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    stripe_subscription_id = db.Column(db.String(100), nullable=True)

    # Email verification
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100), nullable=True)
    email_verified_at = db.Column(db.DateTime, nullable=True)

    # Admin
    is_admin = db.Column(db.Boolean, default=False)

    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    trial_start_date = db.Column(db.DateTime, nullable=True)  # Date de début de la période d'essai Premium

    # Relations
    subscriptions = db.relationship('Subscription', back_populates='user', lazy='dynamic',
                                   cascade='all, delete-orphan')
    notifications = db.relationship('Notification', back_populates='user', lazy='dynamic',
                                   cascade='all, delete-orphan')
    custom_categories = db.relationship('Category', back_populates='user', lazy='dynamic',
                                       cascade='all, delete-orphan')
    custom_services = db.relationship('Service', back_populates='user', lazy='dynamic',
                                     cascade='all, delete-orphan')
    custom_plans = db.relationship('ServicePlan', back_populates='user', lazy='dynamic',
                                  cascade='all, delete-orphan')
    hidden_categories_list = db.relationship('Category', secondary=hidden_categories,
                                            backref=db.backref('hidden_by_users', lazy='dynamic'))
    hidden_services_list = db.relationship('Service', secondary=hidden_services,
                                          backref=db.backref('hidden_by_users', lazy='dynamic'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def set_country(self, country_code):
        """Définit le pays et met à jour automatiquement le fuseau horaire"""
        from app.utils.timezone_mapping import get_timezone_for_country
        self.country = country_code
        if country_code:
            self.timezone = get_timezone_for_country(country_code)
        else:
            self.timezone = 'Europe/Paris'

    def can_add_subscription(self):
        """Vérifie si l'utilisateur peut ajouter un abonnement"""
        if self.is_premium():
            return True
        return self.subscriptions.filter_by(is_active=True).count() < 5

    def is_premium(self):
        """Vérifie si l'utilisateur a un plan Premium (mensuel ou annuel) ou est en période d'essai"""
        # Vérifier si l'utilisateur a un plan Premium payant
        if self.plan and self.plan.is_premium():
            return True

        # Vérifier si l'utilisateur est dans la période d'essai de 7 jours
        if self.trial_start_date:
            trial_end = self.trial_start_date + timedelta(days=7)
            if datetime.utcnow() < trial_end:
                return True

        return False

    def is_on_trial(self):
        """Vérifie si l'utilisateur est actuellement en période d'essai"""
        if not self.trial_start_date:
            return False

        trial_end = self.trial_start_date + timedelta(days=7)
        # En période d'essai si pas de plan payant ET dans les 7 jours
        return datetime.utcnow() < trial_end and (not self.plan or not self.plan.is_premium())

    def get_trial_days_remaining(self):
        """Retourne le nombre de jours restants dans la période d'essai (0 si pas en essai)"""
        if not self.is_on_trial():
            return 0

        trial_end = self.trial_start_date + timedelta(days=7)
        days_remaining = (trial_end - datetime.utcnow()).days
        return max(0, days_remaining + 1)  # +1 pour inclure le jour actuel

    def can_create_custom_category(self):
        """Vérifie si l'utilisateur peut créer des catégories personnalisées
        - Gratuit : max 5 catégories
        - Premium : illimité
        """
        if self.is_premium():
            return True
        return self.custom_categories.count() < 5

    def can_create_custom_service(self):
        """Vérifie si l'utilisateur peut créer des services personnalisés
        - Gratuit : max 5 services
        - Premium : illimité
        """
        if self.is_premium():
            return True
        from app.models import Service
        return Service.query.filter_by(user_id=self.id).count() < 5

    def can_create_custom_plan(self):
        """Vérifie si l'utilisateur peut créer des plans personnalisés
        - Gratuit : max 10 plans
        - Premium : illimité
        """
        if self.is_premium():
            return True
        from app.models import ServicePlan
        return ServicePlan.query.filter_by(user_id=self.id).count() < 10

    def get_custom_categories_count(self):
        """Retourne le nombre de catégories personnalisées créées"""
        return self.custom_categories.count()

    def get_custom_services_count(self):
        """Retourne le nombre de services personnalisés créés"""
        from app.models import Service
        return Service.query.filter_by(user_id=self.id).count()

    def get_custom_plans_count(self):
        """Retourne le nombre de plans personnalisés créés"""
        from app.models import ServicePlan
        return ServicePlan.query.filter_by(user_id=self.id).count()

    def get_active_subscriptions_count(self):
        return self.subscriptions.filter_by(is_active=True).count()

    def is_category_hidden(self, category_id):
        """Vérifie si une catégorie est masquée pour cet utilisateur"""
        return any(cat.id == category_id for cat in self.hidden_categories_list)

    def is_service_hidden(self, service_id):
        """Vérifie si un service est masqué pour cet utilisateur"""
        return any(svc.id == service_id for svc in self.hidden_services_list)

    def generate_verification_token(self):
        """Génère un nouveau token de vérification d'email"""
        self.email_verification_token = secrets.token_urlsafe(32)
        return self.email_verification_token

    def verify_email(self):
        """Marque l'email comme vérifié"""
        self.email_verified = True
        self.email_verified_at = datetime.utcnow()
        self.email_verification_token = None

    def __repr__(self):
        return f'<User {self.email}>'


class Plan(db.Model):
    __tablename__ = 'plans'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)  # 'Free', 'Premium', 'Premium Annual'
    price = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='EUR')
    billing_period = db.Column(db.String(20), default='monthly')  # 'monthly', 'yearly', 'lifetime'
    stripe_price_id = db.Column(db.String(100), nullable=True)
    max_subscriptions = db.Column(db.Integer, nullable=True)  # None = illimité
    description = db.Column(db.Text, nullable=True)
    features = db.Column(db.JSON, nullable=True)  # Liste des fonctionnalités
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship('User', back_populates='plan')

    def is_premium(self):
        """Vérifie si c'est un plan Premium (mensuel ou annuel)"""
        return self.name in ['Premium', 'Premium Annual']

    def __repr__(self):
        return f'<Plan {self.name}>'


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # NULL = catégorie globale
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    logo_url = db.Column(db.String(500), nullable=True)  # Deprecated - kept for backward compatibility
    logo_data = db.Column(db.Text, nullable=True)  # Logo stocké en base64
    logo_mime_type = db.Column(db.String(50), nullable=True)  # Type MIME du logo (image/png, image/jpeg, etc.)
    website_url = db.Column(db.String(500), nullable=True)
    color = db.Column(db.String(7), default='#6c757d')  # Couleur en hex
    icon = db.Column(db.String(50), nullable=True)  # Font Awesome icon class
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    user = db.relationship('User', back_populates='custom_categories')
    subscriptions = db.relationship('Subscription', back_populates='category', lazy='dynamic')

    def is_global(self):
        """Vérifie si c'est une catégorie globale (par défaut)"""
        return self.user_id is None

    def is_custom(self):
        """Vérifie si c'est une catégorie personnalisée"""
        return self.user_id is not None

    def __repr__(self):
        return f'<Category {self.name}>'


class Service(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # NULL = service global
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    logo_url = db.Column(db.String(500), nullable=True)  # Deprecated - kept for backward compatibility
    logo_data = db.Column(db.Text, nullable=True)  # Logo stocké en base64
    logo_mime_type = db.Column(db.String(50), nullable=True)  # Type MIME du logo (image/png, image/jpeg, etc.)
    website_url = db.Column(db.String(500), nullable=True)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    user = db.relationship('User', back_populates='custom_services')
    category = db.relationship('Category', backref='services')
    plans = db.relationship('ServicePlan', back_populates='service', cascade='all, delete-orphan')
    subscriptions = db.relationship('Subscription', back_populates='service')

    def is_global(self):
        """Vérifie si c'est un service global (par défaut)"""
        return self.user_id is None

    def is_custom(self):
        """Vérifie si c'est un service personnalisé"""
        return self.user_id is not None

    def __repr__(self):
        return f'<Service {self.name}>'


class ServicePlan(db.Model):
    __tablename__ = 'service_plans'

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # NULL pour les plans globaux

    name = db.Column(db.String(100), nullable=False)  # Ex: "Standard", "Premium"
    description = db.Column(db.Text, nullable=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='EUR')
    billing_cycle = db.Column(db.String(20), nullable=False)  # 'weekly', 'monthly', 'quarterly', 'yearly'

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    service = db.relationship('Service', back_populates='plans')
    user = db.relationship('User', back_populates='custom_plans')

    def is_custom(self):
        """Vérifie si le plan est personnalisé (créé par un utilisateur)"""
        return self.user_id is not None

    def to_dict(self):
        """Convertit le plan en dictionnaire pour JSON"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'amount': self.amount,
            'currency': self.currency,
            'billing_cycle': self.billing_cycle,
            'is_active': self.is_active
        }

    def __repr__(self):
        return f'<ServicePlan {self.service.name} - {self.name}>'


class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('service_plans.id'), nullable=True)

    # Informations de l'abonnement
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='EUR')

    # Périodicité
    billing_cycle = db.Column(db.String(20), nullable=False)  # 'weekly', 'monthly', 'quarterly', 'yearly'
    start_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    next_billing_date = db.Column(db.Date, nullable=False)

    # État
    is_active = db.Column(db.Boolean, default=True)
    auto_renew = db.Column(db.Boolean, default=True)

    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    # Relations
    user = db.relationship('User', back_populates='subscriptions')
    category = db.relationship('Category', back_populates='subscriptions')
    service = db.relationship('Service', back_populates='subscriptions')
    plan = db.relationship('ServicePlan', backref='subscriptions')
    notifications = db.relationship('Notification', backref='subscription', cascade='all, delete-orphan')

    def calculate_next_billing_date(self):
        """Calcule la prochaine date de facturation"""
        if self.billing_cycle == 'monthly':
            return self.start_date + timedelta(days=30)
        elif self.billing_cycle == 'quarterly':
            return self.start_date + timedelta(days=90)
        elif self.billing_cycle == 'yearly':
            return self.start_date + timedelta(days=365)
        elif self.billing_cycle == 'weekly':
            return self.start_date + timedelta(days=7)
        return self.start_date

    def get_total_paid(self):
        """Calcule le montant total payé depuis le début"""
        if not self.is_active and self.cancelled_at:
            end_date = self.cancelled_at
        else:
            end_date = datetime.utcnow()

        days_elapsed = (end_date - self.created_at).days

        if self.billing_cycle == 'monthly':
            cycles = days_elapsed / 30
        elif self.billing_cycle == 'quarterly':
            cycles = days_elapsed / 90
        elif self.billing_cycle == 'yearly':
            cycles = days_elapsed / 365
        elif self.billing_cycle == 'weekly':
            cycles = days_elapsed / 7
        else:
            cycles = 0

        return round(cycles * self.amount, 2)

    def __repr__(self):
        return f'<Subscription {self.name} - {self.user.email}>'


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=True)

    # Type de notification
    type = db.Column(db.String(50), nullable=False)  # 'renewal', 'expiry', 'payment_failed', etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)

    # État
    is_read = db.Column(db.Boolean, default=False)
    is_sent = db.Column(db.Boolean, default=False)

    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)

    # Relations
    user = db.relationship('User', back_populates='notifications')

    def mark_as_read(self):
        self.is_read = True
        self.read_at = datetime.utcnow()
        db.session.commit()

    def __repr__(self):
        return f'<Notification {self.title} - {self.user.email}>'
