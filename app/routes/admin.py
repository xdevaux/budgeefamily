from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import User, Plan, Category, Service, ServicePlan
from datetime import datetime
import base64
import mimetypes

bp = Blueprint('admin', __name__, url_prefix='/admin')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def admin_required(f):
    """Décorateur pour vérifier que l'utilisateur est administrateur"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Accès refusé. Vous devez être administrateur pour accéder à cette page.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/clients')
@login_required
@admin_required
def clients_list():
    """Liste tous les clients inscrits"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status_filter = request.args.get('status', 'active')  # 'active', 'inactive', 'all'

    # Construire la requête avec le filtre
    query = User.query

    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)
    # Si 'all', pas de filtre

    # Pagination
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    users = pagination.items

    return render_template('admin/clients_list.html',
                         users=users,
                         pagination=pagination,
                         status_filter=status_filter)


@bp.route('/clients/add', methods=['GET', 'POST'])
@login_required
@admin_required
def clients_add():
    """Ajouter un nouveau client"""
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        password = request.form.get('password')
        country = request.form.get('country', 'FR')
        plan_id = request.form.get('plan_id', type=int)
        is_admin = request.form.get('is_admin') == 'on'
        is_active = request.form.get('is_active', 'on') == 'on'

        # Vérifier si l'email existe déjà
        if User.query.filter_by(email=email).first():
            flash('Un utilisateur avec cet email existe déjà.', 'danger')
            return redirect(url_for('admin.clients_add'))

        # Récupérer le plan
        plan = Plan.query.get(plan_id) if plan_id else None

        # Créer l'utilisateur
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            plan=plan,
            is_admin=is_admin,
            is_active=is_active,
            email_verified=True,  # Auto-vérifier les emails pour les utilisateurs créés par admin
            email_verified_at=datetime.utcnow()
        )

        if password:
            user.set_password(password)

        user.set_country(country)  # Définit le pays et le fuseau horaire

        db.session.add(user)
        db.session.commit()

        flash(f'Client {email} créé avec succès !', 'success')
        return redirect(url_for('admin.clients_list'))

    # GET - Afficher le formulaire
    plans = Plan.query.filter_by(is_active=True).all()
    return render_template('admin/clients_add.html', plans=plans)


@bp.route('/clients/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def clients_edit(user_id):
    """Modifier un client existant"""
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        user.email = request.form.get('email')
        user.first_name = request.form.get('first_name')
        user.last_name = request.form.get('last_name')
        user.is_admin = request.form.get('is_admin') == 'on'
        user.is_active = request.form.get('is_active') == 'on'

        # Mettre à jour le pays et le fuseau horaire
        country = request.form.get('country')
        if country:
            user.set_country(country)

        plan_id = request.form.get('plan_id', type=int)
        user.plan = Plan.query.get(plan_id) if plan_id else None

        # Changer le mot de passe si fourni
        new_password = request.form.get('new_password')
        if new_password:
            user.set_password(new_password)

        db.session.commit()

        flash(f'Client {user.email} mis à jour avec succès !', 'success')
        return redirect(url_for('admin.clients_list'))

    # GET - Afficher le formulaire
    plans = Plan.query.filter_by(is_active=True).all()
    return render_template('admin/clients_edit.html', user=user, plans=plans)


@bp.route('/clients/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def clients_delete(user_id):
    """Supprimer un client"""
    user = User.query.get_or_404(user_id)

    # Empêcher la suppression de son propre compte
    if user.id == current_user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'danger')
        return redirect(url_for('admin.clients_list'))

    email = user.email
    db.session.delete(user)
    db.session.commit()

    flash(f'Client {email} supprimé avec succès.', 'success')
    return redirect(url_for('admin.clients_list'))


@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Tableau de bord administrateur"""
    # Statistiques générales
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    admin_users = User.query.filter_by(is_admin=True).count()

    # Récupérer tous les plans actifs
    all_plans = Plan.query.filter_by(is_active=True).all()

    # Compter les utilisateurs non-admin par plan
    plans_stats_with_revenue = []
    total_revenue = 0

    for plan in all_plans:
        # Compter les utilisateurs actifs non-admin pour ce plan
        user_count = User.query.filter(
            User.plan_id == plan.id,
            User.is_active == True,
            (User.is_admin == False) | (User.is_admin == None)
        ).count()

        # Convertir tous les revenus en mensuel
        if plan.billing_period == 'yearly':
            monthly_price = plan.price / 12
        else:
            monthly_price = plan.price

        revenue = monthly_price * user_count
        total_revenue += revenue

        plans_stats_with_revenue.append({
            'name': plan.name,
            'price': plan.price,
            'billing_period': plan.billing_period,
            'user_count': user_count,
            'monthly_revenue': revenue
        })

    # Compter les utilisateurs actifs sans plan (non-admin)
    no_plan_count = User.query.filter(
        User.plan_id == None,
        User.is_active == True,
        (User.is_admin == False) | (User.is_admin == None)
    ).count()

    # Ajouter les administrateurs actifs comme ligne séparée
    admin_count = User.query.filter_by(is_admin=True, is_active=True).count()

    # Utilisateurs récents
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         active_users=active_users,
                         admin_users=admin_users,
                         plans_stats=plans_stats_with_revenue,
                         no_plan_count=no_plan_count,
                         admin_count=admin_count,
                         total_revenue=total_revenue,
                         recent_users=recent_users)


# ========== GESTION DES CATÉGORIES PAR DÉFAUT ==========

@bp.route('/categories')
@login_required
@admin_required
def categories_list():
    """Liste toutes les catégories par défaut (globales)"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Récupérer uniquement les catégories globales (user_id is NULL)
    pagination = Category.query.filter_by(user_id=None).order_by(Category.name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    categories = pagination.items

    return render_template('admin/categories_list.html',
                         categories=categories,
                         pagination=pagination)


@bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
@admin_required
def categories_add():
    """Ajouter une nouvelle catégorie par défaut"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        website_url = request.form.get('website_url')
        color = request.form.get('color', '#6c757d')
        icon = request.form.get('icon')
        is_active = request.form.get('is_active', 'on') == 'on'

        # Gérer l'upload du logo - stockage en base de données
        logo_data = None
        logo_mime_type = None
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename and allowed_file(file.filename):
                # Lire le fichier et le convertir en base64
                file_bytes = file.read()
                logo_data = base64.b64encode(file_bytes).decode('utf-8')

                # Déterminer le MIME type
                mime_type, _ = mimetypes.guess_type(file.filename)
                if mime_type:
                    logo_mime_type = mime_type
                else:
                    # Par défaut, PNG
                    logo_mime_type = 'image/png'

        # Créer la catégorie globale (user_id = None)
        category = Category(
            user_id=None,  # Catégorie globale
            name=name,
            description=description,
            logo_data=logo_data,
            logo_mime_type=logo_mime_type,
            website_url=website_url,
            color=color,
            icon=icon,
            is_active=is_active
        )

        db.session.add(category)
        db.session.commit()

        flash(f'Catégorie "{name}" créée avec succès !', 'success')
        return redirect(url_for('admin.categories_list'))

    return render_template('admin/categories_add.html')


@bp.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def categories_edit(category_id):
    """Modifier une catégorie par défaut existante"""
    category = Category.query.filter_by(id=category_id, user_id=None).first_or_404()

    if request.method == 'POST':
        category.name = request.form.get('name')
        category.description = request.form.get('description')
        category.website_url = request.form.get('website_url')
        category.color = request.form.get('color', '#6c757d')
        category.icon = request.form.get('icon')
        category.is_active = request.form.get('is_active') == 'on'

        # Gérer l'upload du logo - stockage en base de données
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename and allowed_file(file.filename):
                # Lire le fichier et le convertir en base64
                file_bytes = file.read()
                category.logo_data = base64.b64encode(file_bytes).decode('utf-8')

                # Déterminer le MIME type
                mime_type, _ = mimetypes.guess_type(file.filename)
                if mime_type:
                    category.logo_mime_type = mime_type
                else:
                    # Par défaut, PNG
                    category.logo_mime_type = 'image/png'

        db.session.commit()

        flash(f'Catégorie "{category.name}" mise à jour avec succès !', 'success')
        return redirect(url_for('admin.categories_list'))

    return render_template('admin/categories_edit.html', category=category)


@bp.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required
@admin_required
def categories_delete(category_id):
    """Supprimer une catégorie par défaut"""
    category = Category.query.filter_by(id=category_id, user_id=None).first_or_404()

    # Vérifier si des services sont liés à cette catégorie
    services_count = Service.query.filter_by(category_id=category_id).count()
    if services_count > 0:
        flash(f'Impossible de supprimer la catégorie "{category.name}" car {services_count} service(s) y sont liés.', 'danger')
        return redirect(url_for('admin.categories_list'))

    name = category.name
    db.session.delete(category)
    db.session.commit()

    flash(f'Catégorie "{name}" supprimée avec succès.', 'success')
    return redirect(url_for('admin.categories_list'))


# ========== GESTION DES SERVICES PAR DÉFAUT ==========

@bp.route('/services')
@login_required
@admin_required
def services_list():
    """Liste tous les services par défaut (globaux)"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    category_filter = request.args.get('category', type=int)

    # Requête de base : services globaux uniquement
    query = Service.query.filter_by(user_id=None)

    # Filtre par catégorie si spécifié
    if category_filter:
        query = query.filter_by(category_id=category_filter)

    pagination = query.order_by(Service.name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    services = pagination.items

    # Récupérer toutes les catégories pour le filtre
    categories = Category.query.filter_by(user_id=None).order_by(Category.name).all()

    return render_template('admin/services_list.html',
                         services=services,
                         pagination=pagination,
                         categories=categories,
                         category_filter=category_filter)


@bp.route('/services/add', methods=['GET', 'POST'])
@login_required
@admin_required
def services_add():
    """Ajouter un nouveau service par défaut"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        website_url = request.form.get('website_url')
        category_id = request.form.get('category_id', type=int)
        is_active = request.form.get('is_active', 'on') == 'on'

        # Gérer l'upload du logo - stockage en base de données
        logo_data = None
        logo_mime_type = None
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename and allowed_file(file.filename):
                # Lire le fichier et le convertir en base64
                file_bytes = file.read()
                logo_data = base64.b64encode(file_bytes).decode('utf-8')

                # Déterminer le MIME type
                mime_type, _ = mimetypes.guess_type(file.filename)
                if mime_type:
                    logo_mime_type = mime_type
                else:
                    # Par défaut, PNG
                    logo_mime_type = 'image/png'

        # Créer le service global (user_id = None)
        service = Service(
            user_id=None,  # Service global
            category_id=category_id if category_id else None,
            name=name,
            description=description,
            logo_data=logo_data,
            logo_mime_type=logo_mime_type,
            website_url=website_url,
            is_active=is_active
        )

        db.session.add(service)
        db.session.commit()

        flash(f'Service "{name}" créé avec succès !', 'success')
        return redirect(url_for('admin.services_list'))

    # GET - Afficher le formulaire
    categories = Category.query.filter_by(user_id=None, is_active=True).order_by(Category.name).all()
    return render_template('admin/services_add.html', categories=categories)


@bp.route('/services/edit/<int:service_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def services_edit(service_id):
    """Modifier un service par défaut existant"""
    service = Service.query.filter_by(id=service_id, user_id=None).first_or_404()

    if request.method == 'POST':
        service.name = request.form.get('name')
        service.description = request.form.get('description')
        service.website_url = request.form.get('website_url')
        category_id = request.form.get('category_id', type=int)
        service.category_id = category_id if category_id else None
        service.is_active = request.form.get('is_active') == 'on'

        # Gérer l'upload du logo - stockage en base de données
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename and allowed_file(file.filename):
                # Lire le fichier et le convertir en base64
                file_bytes = file.read()
                service.logo_data = base64.b64encode(file_bytes).decode('utf-8')

                # Déterminer le MIME type
                mime_type, _ = mimetypes.guess_type(file.filename)
                if mime_type:
                    service.logo_mime_type = mime_type
                else:
                    # Par défaut, PNG
                    service.logo_mime_type = 'image/png'

        db.session.commit()

        flash(f'Service "{service.name}" mis à jour avec succès !', 'success')
        return redirect(url_for('admin.services_list'))

    # GET - Afficher le formulaire
    categories = Category.query.filter_by(user_id=None, is_active=True).order_by(Category.name).all()
    return render_template('admin/services_edit.html', service=service, categories=categories)


@bp.route('/services/delete/<int:service_id>', methods=['POST'])
@login_required
@admin_required
def services_delete(service_id):
    """Supprimer un service par défaut"""
    service = Service.query.filter_by(id=service_id, user_id=None).first_or_404()

    # Vérifier si des plans sont liés à ce service
    plans_count = ServicePlan.query.filter_by(service_id=service_id).count()
    if plans_count > 0:
        flash(f'Impossible de supprimer le service "{service.name}" car {plans_count} plan(s) y sont liés.', 'danger')
        return redirect(url_for('admin.services_list'))

    name = service.name
    db.session.delete(service)
    db.session.commit()

    flash(f'Service "{name}" supprimé avec succès.', 'success')
    return redirect(url_for('admin.services_list'))


# ========== GESTION DES PLANS DE SERVICES PAR DÉFAUT ==========

@bp.route('/service-plans')
@login_required
@admin_required
def service_plans_list():
    """Liste tous les plans de services par défaut (globaux)"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    service_filter = request.args.get('service', type=int)

    # Requête de base : plans globaux uniquement
    query = ServicePlan.query.filter_by(user_id=None)

    # Filtre par service si spécifié
    if service_filter:
        query = query.filter_by(service_id=service_filter)

    pagination = query.order_by(ServicePlan.service_id, ServicePlan.name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    plans = pagination.items

    # Récupérer tous les services pour le filtre
    services = Service.query.filter_by(user_id=None).order_by(Service.name).all()

    return render_template('admin/service_plans_list.html',
                         plans=plans,
                         pagination=pagination,
                         services=services,
                         service_filter=service_filter)


@bp.route('/service-plans/add', methods=['GET', 'POST'])
@login_required
@admin_required
def service_plans_add():
    """Ajouter un nouveau plan de service par défaut"""
    if request.method == 'POST':
        service_id = request.form.get('service_id', type=int)
        name = request.form.get('name')
        description = request.form.get('description')
        amount = request.form.get('amount', type=float)
        currency = request.form.get('currency', 'EUR')
        billing_cycle = request.form.get('billing_cycle')
        is_active = request.form.get('is_active', 'on') == 'on'

        # Vérifier que le service existe
        service = Service.query.filter_by(id=service_id, user_id=None).first()
        if not service:
            flash('Service invalide.', 'danger')
            return redirect(url_for('admin.service_plans_add'))

        # Créer le plan global (user_id = None)
        plan = ServicePlan(
            user_id=None,  # Plan global
            service_id=service_id,
            name=name,
            description=description,
            amount=amount,
            currency=currency,
            billing_cycle=billing_cycle,
            is_active=is_active
        )

        db.session.add(plan)
        db.session.commit()

        flash(f'Plan "{name}" créé avec succès pour le service "{service.name}" !', 'success')
        return redirect(url_for('admin.service_plans_list'))

    # GET - Afficher le formulaire
    services = Service.query.filter_by(user_id=None, is_active=True).order_by(Service.name).all()
    return render_template('admin/service_plans_add.html', services=services)


@bp.route('/service-plans/edit/<int:plan_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def service_plans_edit(plan_id):
    """Modifier un plan de service par défaut existant"""
    plan = ServicePlan.query.filter_by(id=plan_id, user_id=None).first_or_404()

    if request.method == 'POST':
        service_id = request.form.get('service_id', type=int)

        # Vérifier que le service existe
        service = Service.query.filter_by(id=service_id, user_id=None).first()
        if not service:
            flash('Service invalide.', 'danger')
            return redirect(url_for('admin.service_plans_edit', plan_id=plan_id))

        plan.service_id = service_id
        plan.name = request.form.get('name')
        plan.description = request.form.get('description')
        plan.amount = request.form.get('amount', type=float)
        plan.currency = request.form.get('currency', 'EUR')
        plan.billing_cycle = request.form.get('billing_cycle')
        plan.is_active = request.form.get('is_active') == 'on'

        db.session.commit()

        flash(f'Plan "{plan.name}" mis à jour avec succès !', 'success')
        return redirect(url_for('admin.service_plans_list'))

    # GET - Afficher le formulaire
    services = Service.query.filter_by(user_id=None, is_active=True).order_by(Service.name).all()
    return render_template('admin/service_plans_edit.html', plan=plan, services=services)


@bp.route('/service-plans/delete/<int:plan_id>', methods=['POST'])
@login_required
@admin_required
def service_plans_delete(plan_id):
    """Supprimer un plan de service par défaut"""
    plan = ServicePlan.query.filter_by(id=plan_id, user_id=None).first_or_404()

    name = plan.name
    service_name = plan.service.name
    db.session.delete(plan)
    db.session.commit()

    flash(f'Plan "{name}" du service "{service_name}" supprimé avec succès.', 'success')
    return redirect(url_for('admin.service_plans_list'))
