from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
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
    date_of_birth = db.Column(db.Date, nullable=True)  # Date de naissance
    avatar_url = db.Column(db.String(500), nullable=True)
    default_currency = db.Column(db.String(3), default='EUR')  # Devise par défaut
    country = db.Column(db.String(2), nullable=True)  # Code pays ISO 3166-1 alpha-2 (FR, US, etc.)
    timezone = db.Column(db.String(50), default='Europe/Paris')  # Fuseau horaire de l'utilisateur
    language = db.Column(db.String(2), default='fr')  # Langue de l'utilisateur (fr, en, es, it, de, pt)

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

    # Notifications
    email_notifications = db.Column(db.Boolean, default=False)  # Recevoir un email à chaque notification

    # Stockage
    storage_limit = db.Column(db.BigInteger, default=5368709120)  # Limite de stockage en octets (5 Go par défaut)

    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    # Relations
    subscriptions = db.relationship('Subscription', back_populates='user', lazy='dynamic',
                                   cascade='all, delete-orphan')
    notifications = db.relationship('Notification', foreign_keys='Notification.user_id',
                                   back_populates='user', lazy='dynamic',
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

    def can_add_revenue(self):
        """Vérifie si l'utilisateur peut ajouter un revenu
        - Gratuit : max 1 revenu
        - Premium : illimité
        """
        if self.is_premium():
            return True
        return self.revenues.filter_by(is_active=True).count() < 1

    def can_add_credit(self):
        """Vérifie si l'utilisateur peut ajouter un crédit
        - Gratuit : max 1 crédit
        - Premium : illimité
        """
        if self.is_premium():
            return True
        return self.credits.filter_by(is_active=True).count() < 1

    def can_add_installment_payment(self):
        """Vérifie si l'utilisateur peut ajouter un paiement en plusieurs fois
        - Gratuit : max 1 paiement
        - Premium : illimité
        """
        if self.is_premium():
            return True
        return self.installment_payments.filter_by(is_active=True).count() < 1

    def is_premium(self):
        """Vérifie si l'utilisateur a un plan Premium (mensuel ou annuel)"""
        return self.plan and self.plan.is_premium()

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

    def can_add_reminder(self):
        """Vérifie si l'utilisateur peut ajouter un rappel
        - Gratuit : max 3 rappels
        - Premium : illimité
        """
        if self.is_premium():
            return True
        return self.reminders.filter_by(is_active=True).count() < 3

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

    def get_storage_used(self):
        """Calcule l'espace de stockage utilisé par tous les documents de l'utilisateur (en octets)"""
        total_size = 0

        # Documents des employeurs
        for doc in self.employer_documents.all():
            if doc.file_size:
                total_size += doc.file_size

        # Documents des banques
        for doc in self.bank_documents.all():
            if doc.file_size:
                total_size += doc.file_size

        # Documents des crédits
        for doc in self.credit_documents.all():
            if doc.file_size:
                total_size += doc.file_size

        return total_size

    def get_storage_used_mb(self):
        """Retourne l'espace utilisé en Mo"""
        return round(self.get_storage_used() / (1024 * 1024), 2)

    def get_storage_used_gb(self):
        """Retourne l'espace utilisé en Go"""
        return round(self.get_storage_used() / (1024 * 1024 * 1024), 2)

    def get_storage_limit_gb(self):
        """Retourne la limite de stockage en Go"""
        limit = self.storage_limit if self.storage_limit is not None else self.get_default_storage_limit()
        return round(limit / (1024 * 1024 * 1024), 2)

    def get_storage_percentage(self):
        """Retourne le pourcentage d'espace utilisé"""
        limit = self.storage_limit if self.storage_limit is not None else self.get_default_storage_limit()
        if limit == 0:
            return 0
        return round((self.get_storage_used() / limit) * 100, 2)

    def has_storage_available(self, file_size):
        """Vérifie si l'utilisateur a suffisamment d'espace pour un nouveau fichier"""
        limit = self.storage_limit if self.storage_limit is not None else self.get_default_storage_limit()
        return (self.get_storage_used() + file_size) <= limit

    def get_default_storage_limit(self):
        """Retourne la limite de stockage par défaut selon le plan"""
        if self.is_premium():
            return 21474836480  # 20 Go en octets
        else:
            return 5368709120  # 5 Go en octets

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
    category_type = db.Column(db.String(20), nullable=False, default='all')  # 'all', 'subscription', 'card_purchase'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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

    # Montant total payé
    total_paid = db.Column(db.Float, default=0.0, nullable=False)

    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    # Relations
    user = db.relationship('User', back_populates='subscriptions')
    category = db.relationship('Category', back_populates='subscriptions')
    service = db.relationship('Service', back_populates='subscriptions')
    plan = db.relationship('ServicePlan', backref='subscriptions')
    notifications = db.relationship('Notification', backref='subscription')

    def calculate_next_billing_date(self):
        """Calcule la prochaine date de facturation"""
        if self.billing_cycle == 'monthly':
            return self.start_date + relativedelta(months=1)
        elif self.billing_cycle == 'quarterly':
            return self.start_date + relativedelta(months=3)
        elif self.billing_cycle == 'yearly':
            return self.start_date + relativedelta(years=1)
        elif self.billing_cycle == 'weekly':
            return self.start_date + timedelta(weeks=1)
        return self.start_date

    def get_total_paid(self):
        """Retourne le montant total payé depuis le début"""
        return round(self.total_paid, 2)

    def get_display_date(self):
        """Retourne la date à afficher : start_date si future ou égale à aujourd'hui, sinon next_billing_date"""
        from datetime import date
        today = date.today()
        if self.start_date >= today:
            return self.start_date
        return self.next_billing_date

    def __repr__(self):
        return f'<Subscription {self.name} - {self.user.email}>'


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id', ondelete='SET NULL'), nullable=True)
    credit_id = db.Column(db.Integer, db.ForeignKey('credits.id', ondelete='SET NULL'), nullable=True)
    revenue_id = db.Column(db.Integer, db.ForeignKey('revenues.id', ondelete='SET NULL'), nullable=True)
    installment_payment_id = db.Column(db.Integer, db.ForeignKey('installment_payments.id', ondelete='SET NULL'), nullable=True)
    reminder_id = db.Column(db.Integer, db.ForeignKey('reminders.id', ondelete='SET NULL'), nullable=True)

    # Utilisateur qui a créé l'action à l'origine de la notification
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Type de notification
    type = db.Column(db.String(50), nullable=False)  # 'renewal', 'expiry', 'payment_failed', etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)

    # État
    is_read = db.Column(db.Boolean, default=False)
    is_sent = db.Column(db.Boolean, default=False)
    archived = db.Column(db.Boolean, default=False)

    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    archived_at = db.Column(db.DateTime, nullable=True)

    # Relations
    user = db.relationship('User', foreign_keys=[user_id], back_populates='notifications')
    created_by_user = db.relationship('User', foreign_keys=[created_by_user_id])
    credit = db.relationship('Credit', foreign_keys=[credit_id])
    revenue = db.relationship('Revenue', foreign_keys=[revenue_id])
    reminder = db.relationship('Reminder', foreign_keys=[reminder_id])

    def mark_as_read(self):
        self.is_read = True
        self.read_at = datetime.utcnow()
        db.session.commit()

    def archive(self):
        """Archive la notification"""
        self.archived = True
        self.archived_at = datetime.utcnow()
        db.session.commit()

    def __repr__(self):
        return f'<Notification {self.title} - {self.user.email}>'


class CreditType(db.Model):
    __tablename__ = 'credit_types'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # NULL = type global

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), nullable=True)  # Font Awesome icon class
    color = db.Column(db.String(7), default='#6c757d')  # Couleur en hex

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('custom_credit_types', lazy='dynamic', cascade='all, delete-orphan'))
    credits = db.relationship('Credit', back_populates='credit_type_obj', lazy='dynamic')

    def is_global(self):
        """Vérifie si c'est un type global (par défaut)"""
        return self.user_id is None

    def is_custom(self):
        """Vérifie si c'est un type personnalisé"""
        return self.user_id is not None

    def __repr__(self):
        return f'<CreditType {self.name}>'


class Credit(db.Model):
    __tablename__ = 'credits'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    credit_type_id = db.Column(db.Integer, db.ForeignKey('credit_types.id'), nullable=True)
    bank_id = db.Column(db.Integer, db.ForeignKey('banks.id'), nullable=True)

    # Informations du crédit
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='EUR')

    # Type de crédit (legacy - gardé pour compatibilité)
    credit_type = db.Column(db.String(50), nullable=True)  # 'loan', 'mortgage', 'car_loan', 'personal_loan', 'other'

    # Périodicité
    billing_cycle = db.Column(db.String(20), nullable=False)  # 'monthly', 'quarterly', 'yearly'
    start_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.Date, nullable=True)  # Date de fin du crédit
    next_payment_date = db.Column(db.Date, nullable=False)

    # Informations sur le crédit
    total_amount = db.Column(db.Float, nullable=True)  # Montant total du crédit
    remaining_amount = db.Column(db.Float, nullable=True)  # Montant restant à rembourser
    interest_rate = db.Column(db.Float, nullable=True)  # Taux d'intérêt annuel (en %)

    # État
    is_active = db.Column(db.Boolean, default=True)

    # Montant total payé
    total_paid = db.Column(db.Float, default=0.0, nullable=False)

    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)

    # Relations
    user = db.relationship('User', backref=db.backref('credits', lazy='dynamic', cascade='all, delete-orphan'))
    category = db.relationship('Category', backref='credits')
    credit_type_obj = db.relationship('CreditType', back_populates='credits')
    bank = db.relationship('Bank', back_populates='credits')
    documents = db.relationship('CreditDocument', back_populates='credit', lazy='dynamic', cascade='all, delete-orphan')

    def calculate_next_payment_date(self):
        """Calcule la prochaine date de paiement"""
        if self.billing_cycle == 'monthly':
            return self.start_date + relativedelta(months=1)
        elif self.billing_cycle == 'quarterly':
            return self.start_date + relativedelta(months=3)
        elif self.billing_cycle == 'yearly':
            return self.start_date + relativedelta(years=1)
        return self.start_date

    def get_total_paid(self):
        """Retourne le montant total payé depuis le début"""
        return round(self.total_paid, 2)

    def get_progress_percentage(self):
        """Calcule le pourcentage de remboursement"""
        if not self.total_amount or self.total_amount == 0:
            return 0
        if not self.remaining_amount:
            return 100
        paid = self.total_amount - self.remaining_amount
        return round((paid / self.total_amount) * 100, 2)

    def __repr__(self):
        return f'<Credit {self.name} - {self.user.email}>'


class Employer(db.Model):
    __tablename__ = 'employers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Informations de l'employeur
    name = db.Column(db.String(100), nullable=False)
    logo_data = db.Column(db.Text, nullable=True)  # Logo en base64
    logo_mime_type = db.Column(db.String(50), nullable=True)

    # Coordonnees
    address = db.Column(db.String(255), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    siret = db.Column(db.String(50), nullable=True)

    # Emploi
    job_title = db.Column(db.String(100), nullable=True)  # Poste occupe
    hire_date = db.Column(db.Date, nullable=True)  # Date d'embauche
    end_date = db.Column(db.Date, nullable=True)  # Date de fin (si termine)
    contract_type = db.Column(db.String(50), nullable=True)  # CDI, CDD, Freelance, etc.

    # Notes
    notes = db.Column(db.Text, nullable=True)

    # Etat
    is_active = db.Column(db.Boolean, default=True)

    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('employers', lazy='dynamic', cascade='all, delete-orphan'))
    revenues = db.relationship('Revenue', back_populates='employer', lazy='dynamic')
    documents = db.relationship('EmployerDocument', back_populates='employer', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Employer {self.name}>'


class EmployerDocument(db.Model):
    __tablename__ = 'employer_documents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    employer_id = db.Column(db.Integer, db.ForeignKey('employers.id'), nullable=False)

    # Informations du document
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    document_type = db.Column(db.String(50), nullable=False)  # 'contract', 'payslip', 'certificate', 'other'

    # Fichier
    file_data = db.Column(db.LargeBinary, nullable=True)  # Fichier stocke en binaire
    file_name = db.Column(db.String(255), nullable=True)
    file_mime_type = db.Column(db.String(100), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)  # Taille en bytes

    # Metadonnees
    document_date = db.Column(db.Date, nullable=True)  # Date du document (ex: mois de la fiche de paie)
    year = db.Column(db.Integer, nullable=True)  # Annee pour classement
    month = db.Column(db.Integer, nullable=True)  # Mois pour classement (fiches de paie)

    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('employer_documents', lazy='dynamic', cascade='all, delete-orphan'))
    employer = db.relationship('Employer', back_populates='documents')

    def get_file_size_display(self):
        """Retourne la taille du fichier en format lisible"""
        if not self.file_size:
            return "0 Ko"
        if self.file_size < 1024:
            return f"{self.file_size} o"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} Ko"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} Mo"

    def __repr__(self):
        return f'<EmployerDocument {self.name}>'


class Revenue(db.Model):
    __tablename__ = 'revenues'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    employer_id = db.Column(db.Integer, db.ForeignKey('employers.id'), nullable=True)

    # Informations du revenu
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    company = db.Column(db.String(100), nullable=True)  # Legacy - garde pour compatibilite
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='EUR')

    # Type de revenu
    revenue_type = db.Column(db.String(50), nullable=True)  # 'salary', 'freelance', 'rental', 'investment', 'other'

    # Periodicite
    billing_cycle = db.Column(db.String(20), nullable=False)  # 'monthly', 'quarterly', 'yearly'
    start_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    next_payment_date = db.Column(db.Date, nullable=False)

    # Etat
    is_active = db.Column(db.Boolean, default=True)

    # Montant total reçu
    total_paid = db.Column(db.Float, default=0.0, nullable=False)

    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('revenues', lazy='dynamic', cascade='all, delete-orphan'))
    employer = db.relationship('Employer', back_populates='revenues')

    def calculate_next_payment_date(self):
        """Calcule la prochaine date de paiement"""
        if self.billing_cycle == 'monthly':
            return self.start_date + relativedelta(months=1)
        elif self.billing_cycle == 'quarterly':
            return self.start_date + relativedelta(months=3)
        elif self.billing_cycle == 'yearly':
            return self.start_date + relativedelta(years=1)
        return self.start_date

    def get_monthly_amount(self):
        """Calcule le montant mensuel equivalent"""
        if self.billing_cycle == 'monthly':
            return self.amount
        elif self.billing_cycle == 'quarterly':
            return self.amount / 3
        elif self.billing_cycle == 'yearly':
            return self.amount / 12
        return self.amount

    def get_total_paid(self):
        """Retourne le montant total reçu depuis le début"""
        return round(self.total_paid, 2)

    def __repr__(self):
        return f'<Revenue {self.name} - {self.user.email}>'


class Bank(db.Model):
    __tablename__ = 'banks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Informations de la banque
    name = db.Column(db.String(100), nullable=False)
    logo_data = db.Column(db.Text, nullable=True)  # Logo en base64
    logo_mime_type = db.Column(db.String(50), nullable=True)

    # Coordonnées
    address = db.Column(db.String(255), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    website = db.Column(db.String(255), nullable=True)

    # Informations du compte
    account_number = db.Column(db.String(100), nullable=True)  # Numéro de compte
    iban = db.Column(db.String(34), nullable=True)
    bic = db.Column(db.String(11), nullable=True)

    # Notes
    notes = db.Column(db.Text, nullable=True)

    # État
    is_active = db.Column(db.Boolean, default=True)

    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('banks', lazy='dynamic', cascade='all, delete-orphan'))
    credits = db.relationship('Credit', back_populates='bank', lazy='dynamic')
    documents = db.relationship('BankDocument', back_populates='bank', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Bank {self.name}>'


class BankDocument(db.Model):
    __tablename__ = 'bank_documents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bank_id = db.Column(db.Integer, db.ForeignKey('banks.id'), nullable=False)

    # Informations du document
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    document_type = db.Column(db.String(50), nullable=False)  # 'contract', 'statement', 'other'

    # Fichier
    file_data = db.Column(db.LargeBinary, nullable=True)  # Fichier stocké en binaire
    file_name = db.Column(db.String(255), nullable=True)
    file_mime_type = db.Column(db.String(100), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)  # Taille en bytes

    # Métadonnées
    document_date = db.Column(db.Date, nullable=True)  # Date du document
    year = db.Column(db.Integer, nullable=True)  # Année pour classement
    month = db.Column(db.Integer, nullable=True)  # Mois pour classement

    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('bank_documents', lazy='dynamic', cascade='all, delete-orphan'))
    bank = db.relationship('Bank', back_populates='documents')

    def __repr__(self):
        return f'<BankDocument {self.name}>'


class CreditDocument(db.Model):
    __tablename__ = 'credit_documents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    credit_id = db.Column(db.Integer, db.ForeignKey('credits.id'), nullable=False)

    # Informations du document
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    document_type = db.Column(db.String(50), nullable=False)  # 'contract', 'statement', 'insurance', 'other'

    # Fichier
    file_data = db.Column(db.LargeBinary, nullable=True)  # Fichier stocké en binaire
    file_name = db.Column(db.String(255), nullable=True)
    file_mime_type = db.Column(db.String(100), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)  # Taille en bytes

    # Métadonnées
    document_date = db.Column(db.Date, nullable=True)  # Date du document
    year = db.Column(db.Integer, nullable=True)  # Année pour classement
    month = db.Column(db.Integer, nullable=True)  # Mois pour classement

    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('credit_documents', lazy='dynamic', cascade='all, delete-orphan'))
    credit = db.relationship('Credit', back_populates='documents')

    def __repr__(self):
        return f'<CreditDocument {self.name}>'


class InstallmentPayment(db.Model):
    """Modèle pour les paiements en plusieurs fois (type ALMA, Klarna, etc.)"""
    __tablename__ = 'installment_payments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    credit_type_id = db.Column(db.Integer, db.ForeignKey('credit_types.id'), nullable=True)

    # Informations du produit/service
    name = db.Column(db.String(200), nullable=False)  # Ex: "Four Darty"
    description = db.Column(db.Text, nullable=True)
    merchant = db.Column(db.String(100), nullable=True)  # Ex: "Darty"

    # Informations du paiement
    total_amount = db.Column(db.Float, nullable=False)  # Montant total
    installment_amount = db.Column(db.Float, nullable=False)  # Montant de chaque mensualité
    number_of_installments = db.Column(db.Integer, nullable=False)  # Nombre de mensualités
    installments_paid = db.Column(db.Integer, default=0)  # Nombre de mensualités payées

    # Frais
    has_fees = db.Column(db.Boolean, default=False)  # Avec ou sans frais
    fees_amount = db.Column(db.Float, default=0.0)  # Montant total des frais

    # Fournisseur du paiement
    provider = db.Column(db.String(50), nullable=True)  # 'ALMA', 'Klarna', 'PayPal', 'Amazon', 'Autre'

    # Catégorie de produit
    product_category = db.Column(db.String(100), nullable=True)  # 'Informatique', 'Électroménager', etc.

    # Dates
    start_date = db.Column(db.Date, nullable=False)
    next_payment_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)  # Date de fin calculée

    # Devise
    currency = db.Column(db.String(3), default='EUR')

    # État
    is_active = db.Column(db.Boolean, default=True)
    is_completed = db.Column(db.Boolean, default=False)

    # Dates de suivi
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relations
    user = db.relationship('User', backref=db.backref('installment_payments', lazy='dynamic', cascade='all, delete-orphan'))
    category = db.relationship('Category', backref='installment_payments')
    credit_type_obj = db.relationship('CreditType', backref='installment_payments')

    def calculate_remaining_amount(self):
        """Calcule le montant restant à payer"""
        remaining_installments = self.number_of_installments - self.installments_paid
        return remaining_installments * self.installment_amount

    def calculate_next_payment_date(self):
        """Calcule la prochaine date de paiement (mensuel)"""
        return self.next_payment_date + relativedelta(months=1)

    def process_payment(self):
        """Traite un paiement mensuel"""
        if self.installments_paid < self.number_of_installments:
            self.installments_paid += 1
            self.next_payment_date = self.calculate_next_payment_date()

            # Marquer comme terminé si toutes les mensualités sont payées
            if self.installments_paid >= self.number_of_installments:
                self.is_completed = True
                self.is_active = False
                self.completed_at = datetime.utcnow()

            db.session.commit()
            return True
        return False

    def get_progress_percentage(self):
        """Retourne le pourcentage de progression"""
        if self.number_of_installments == 0:
            return 0
        return int((self.installments_paid / self.number_of_installments) * 100)

    def __repr__(self):
        return f'<InstallmentPayment {self.name} - {self.installments_paid}/{self.number_of_installments}>'


class Transaction(db.Model):
    """Modèle pour l'historique de toutes les transactions financières"""
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # Date de la transaction (date réelle du mouvement)
    transaction_date = db.Column(db.Date, nullable=False, index=True)

    # Type de transaction
    transaction_type = db.Column(db.String(20), nullable=False)  # 'revenue', 'subscription', 'credit', 'installment'

    # Référence vers l'entité source (pour traçabilité)
    source_id = db.Column(db.Integer, nullable=False)
    source_type = db.Column(db.String(20), nullable=False)  # 'revenue', 'subscription', 'credit', 'installment'

    # Informations du mouvement (snapshot au moment de la transaction)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='EUR', nullable=False)

    # Positif (revenu) ou négatif (dépense)
    is_positive = db.Column(db.Boolean, nullable=False)

    # Catégorie (snapshot)
    category_name = db.Column(db.String(100), nullable=True)

    # Pointage
    is_pointed = db.Column(db.Boolean, default=False, nullable=False)

    # Statut
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)  # 'pending', 'completed', 'cancelled'

    # Notes optionnelles
    notes = db.Column(db.Text, nullable=True)

    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relations
    user = db.relationship('User', backref=db.backref('transactions', lazy='dynamic', cascade='all, delete-orphan'))

    def get_source_object(self):
        """Retourne l'objet source de la transaction"""
        if self.source_type == 'revenue':
            return Revenue.query.get(self.source_id)
        elif self.source_type == 'subscription':
            return Subscription.query.get(self.source_id)
        elif self.source_type == 'credit':
            return Credit.query.get(self.source_id)
        elif self.source_type == 'installment':
            return InstallmentPayment.query.get(self.source_id)
        elif self.source_type == 'check':
            return Check.query.get(self.source_id)
        return None

    def __repr__(self):
        return f'<Transaction {self.name} - {self.amount} {self.currency} - {self.transaction_date}>'


class Checkbook(db.Model):
    """Modèle pour les chéquiers"""
    __tablename__ = 'checkbooks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # Informations du chéquier
    name = db.Column(db.String(200), nullable=False)  # Nom du chéquier (ex: "Chéquier 2024")
    bank_id = db.Column(db.Integer, db.ForeignKey('banks.id'), nullable=True)  # Banque associée
    start_number = db.Column(db.Integer, nullable=False)  # Numéro du premier chèque
    end_number = db.Column(db.Integer, nullable=False)  # Numéro du dernier chèque

    # Statut
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    status = db.Column(db.String(20), default='active', nullable=False)  # 'active', 'finished'

    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relations
    user = db.relationship('User', backref=db.backref('checkbooks', lazy='dynamic', cascade='all, delete-orphan'))
    bank = db.relationship('Bank', backref=db.backref('checkbooks', lazy='dynamic'))
    checks = db.relationship('Check', back_populates='checkbook', lazy='dynamic', cascade='all, delete-orphan')

    def total_checks(self):
        """Retourne le nombre total de chèques dans le chéquier"""
        return self.end_number - self.start_number + 1

    def available_checks_count(self):
        """Nombre de chèques disponibles"""
        return self.checks.filter_by(status='available').count()

    def used_checks_count(self):
        """Nombre de chèques utilisés"""
        return self.checks.filter_by(status='used').count()

    def cancelled_checks_count(self):
        """Nombre de chèques annulés"""
        return self.checks.filter_by(status='cancelled').count()

    def remaining_checks_count(self):
        """Nombre de chèques restants (disponibles)"""
        return self.available_checks_count()

    def is_finished(self):
        """Vérifie si tous les chèques sont consommés (utilisés ou annulés)"""
        return self.available_checks_count() == 0 and self.checks.count() > 0

    def auto_finish_if_complete(self):
        """Passe automatiquement en 'finished' si tous les chèques sont consommés"""
        if self.is_finished() and self.status == 'active':
            self.status = 'finished'
            db.session.commit()

    def get_next_available_check(self):
        """Récupère le prochain chèque disponible (par ordre de numéro)"""
        return self.checks.filter_by(status='available').order_by(Check.check_number).first()

    def __repr__(self):
        return f'<Checkbook {self.name} - {self.start_number} to {self.end_number}>'


class Check(db.Model):
    """Modèle pour les chèques individuels"""
    __tablename__ = 'checks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    checkbook_id = db.Column(db.Integer, db.ForeignKey('checkbooks.id'), nullable=False, index=True)

    # Informations du chèque
    check_number = db.Column(db.Integer, nullable=False)  # Numéro du chèque
    amount = db.Column(db.Float, nullable=False)  # Montant du chèque
    currency = db.Column(db.String(3), default='EUR', nullable=False)
    payee = db.Column(db.String(200), nullable=True)  # Bénéficiaire
    description = db.Column(db.Text, nullable=True)  # Description/Memo

    # Date
    check_date = db.Column(db.Date, nullable=False)  # Date du chèque

    # Statut
    status = db.Column(db.String(20), default='pending', nullable=False)  # 'pending', 'cashed', 'cancelled'

    # Dates système
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relations
    user = db.relationship('User', backref=db.backref('checks', lazy='dynamic', cascade='all, delete-orphan'))
    checkbook = db.relationship('Checkbook', back_populates='checks')

    def __repr__(self):
        return f'<Check #{self.check_number} - {self.amount} {self.currency} - {self.payee}>'


class CardPurchase(db.Model):
    """Modèle pour les achats par carte bancaire"""
    __tablename__ = 'card_purchases'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # Informations de l'achat
    purchase_date = db.Column(db.DateTime, nullable=False, index=True)
    merchant_name = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='EUR', nullable=False)

    # Catégorie
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    category_name = db.Column(db.String(100))  # Snapshot pour historique

    # Informations complémentaires
    description = db.Column(db.Text)
    notes = db.Column(db.Text)

    # Image du reçu (stockage BLOB comme les autres documents)
    receipt_image_data = db.Column(db.LargeBinary)
    receipt_image_name = db.Column(db.String(255))
    receipt_image_mime_type = db.Column(db.String(100))
    receipt_image_size = db.Column(db.Integer)

    # Métadonnées OCR
    ocr_confidence = db.Column(db.Float)  # Score de confiance (0-100)
    was_manually_edited = db.Column(db.Boolean, default=False)
    entry_method = db.Column(db.String(20), nullable=False, default='manual')  # 'manual' ou 'ocr'

    # Statut
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relations
    user = db.relationship('User', backref=db.backref('card_purchases', lazy='dynamic'))
    category = db.relationship('Category', backref=db.backref('card_purchases', lazy='dynamic'))

    def __repr__(self):
        return f'<CardPurchase {self.merchant_name} - {self.amount}€>'

    def to_dict(self):
        """Convertit l'achat en dictionnaire (utile pour JSON/API)"""
        return {
            'id': self.id,
            'purchase_date': self.purchase_date.isoformat(),
            'merchant_name': self.merchant_name,
            'amount': self.amount,
            'currency': self.currency,
            'category_name': self.category_name,
            'description': self.description,
            'ocr_confidence': self.ocr_confidence,
            'was_manually_edited': self.was_manually_edited
        }


class Provider(db.Model):
    """Modèle pour les prestataires de services"""
    __tablename__ = 'providers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    provider_type = db.Column(db.String(200), nullable=True)  # Type de prestataire (champ libre)
    phone = db.Column(db.String(50), nullable=True)  # Téléphone
    email = db.Column(db.String(200), nullable=True)  # Email
    address = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('providers', lazy='dynamic'))
    reminders = db.relationship('Reminder', backref='provider', lazy='dynamic')

    def __repr__(self):
        return f'<Provider {self.name}>'


class Reminder(db.Model):
    """Modèle pour les rappels de prestations périodiques"""
    __tablename__ = 'reminders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=True)

    # Informations de la prestation
    name = db.Column(db.String(200), nullable=False)  # Ex: "Entretien chaudière"
    description = db.Column(db.Text, nullable=True)

    # Date du prochain RDV (mois/année)
    reminder_month = db.Column(db.Integer, nullable=False)  # 1-12
    reminder_year = db.Column(db.Integer, nullable=False)

    # Coût estimé
    estimated_cost = db.Column(db.Float, nullable=True)
    currency = db.Column(db.String(3), default='EUR')

    # Statut du RDV
    appointment_booked = db.Column(db.Boolean, default=False)
    appointment_date = db.Column(db.Date, nullable=True)  # Date exacte si RDV pris

    # Périodicité
    recurrence = db.Column(db.String(20), default='annual')
    # Options: 'annual', 'semiannual', 'biennial', 'once'

    # État
    is_active = db.Column(db.Boolean, default=True)
    archived_at = db.Column(db.DateTime, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('reminders', lazy='dynamic'))
    documents = db.relationship('ReminderDocument', backref='reminder', lazy='dynamic',
                               cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Reminder {self.name} - {self.reminder_month}/{self.reminder_year}>'


class ReminderDocument(db.Model):
    """Modèle pour les documents associés aux rappels"""
    __tablename__ = 'reminder_documents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reminder_id = db.Column(db.Integer, db.ForeignKey('reminders.id'), nullable=False)

    # Métadonnées document
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    document_type = db.Column(db.String(50), nullable=False)
    # Types: 'invoice', 'contract', 'report', 'certificate', 'other'

    # Fichier (stockage en base)
    file_data = db.Column(db.LargeBinary, nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    file_mime_type = db.Column(db.String(100), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)

    # Classification
    document_date = db.Column(db.Date, nullable=True)
    year = db.Column(db.Integer, nullable=True)
    month = db.Column(db.Integer, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('reminder_documents', lazy='dynamic'))

    def get_file_size_display(self):
        """Retourne la taille formatée du fichier"""
        if not self.file_size:
            return "0 KB"
        size_kb = self.file_size / 1024
        if size_kb < 1024:
            return f"{size_kb:.1f} KB"
        return f"{size_kb / 1024:.1f} MB"

    def __repr__(self):
        return f'<ReminderDocument {self.name}>'
