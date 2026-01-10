from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Service, ServicePlan, Category
from werkzeug.utils import secure_filename
import os
import base64
import mimetypes

bp = Blueprint('services', __name__, url_prefix='/services')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_user_services():
    """Récupère les services globaux et personnalisés de l'utilisateur actuel"""
    # Services globaux (par défaut) - non masqués
    all_global_services = Service.query.filter_by(user_id=None).order_by(Service.name).all()

    # Services personnalisés de l'utilisateur
    if current_user.is_authenticated:
        # Filtrer les services masqués
        hidden_ids = [svc.id for svc in current_user.hidden_services_list]
        global_services = [svc for svc in all_global_services if svc.id not in hidden_ids]

        custom_services = Service.query.filter_by(user_id=current_user.id).order_by(Service.name).all()
        return global_services + custom_services

    return all_global_services


@bp.route('/')
@login_required
def list():
    # Services globaux - non masqués
    all_global_services = Service.query.filter_by(user_id=None, is_active=True).order_by(Service.name).all()

    # Filtrer les services masqués par l'utilisateur
    hidden_ids = [svc.id for svc in current_user.hidden_services_list]
    global_services = [svc for svc in all_global_services if svc.id not in hidden_ids]

    # Services personnalisés de l'utilisateur
    custom_services = Service.query.filter_by(user_id=current_user.id).order_by(Service.name).all()

    return render_template('services/list.html',
                         global_services=global_services,
                         custom_services=custom_services)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    # Vérifier que l'utilisateur peut créer un service
    if not current_user.can_create_custom_service():
        if current_user.is_premium():
            flash('Vous avez atteint la limite de services personnalisés.', 'warning')
        else:
            count = current_user.get_custom_services_count()
            flash(f'Vous avez atteint la limite de 5 services personnalisés pour le plan gratuit ({count}/5). Passez au plan Premium pour créer un nombre illimité de services.', 'warning')
        return redirect(url_for('services.list'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        website_url = request.form.get('website_url')
        category_id = request.form.get('category_id', type=int)

        # Gestion du logo - stockage en base de données
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

        service = Service(
            user_id=current_user.id,
            name=name,
            description=description,
            logo_data=logo_data,
            logo_mime_type=logo_mime_type,
            website_url=website_url,
            category_id=category_id if category_id else None
        )

        db.session.add(service)
        db.session.commit()

        flash(f'Le service "{name}" a été créé avec succès !', 'success')
        return redirect(url_for('services.list'))

    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    return render_template('services/add.html', categories=categories)


@bp.route('/<int:service_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(service_id):
    service = Service.query.get_or_404(service_id)

    # Vérifier que l'utilisateur peut modifier ce service
    if service.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce service.', 'danger')
        return redirect(url_for('services.list'))

    if request.method == 'POST':
        service.name = request.form.get('name')
        service.description = request.form.get('description')
        service.website_url = request.form.get('website_url')
        service.category_id = request.form.get('category_id', type=int) or None

        # Gestion du logo - stockage en base de données
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

        flash(f'Le service "{service.name}" a été mis à jour.', 'success')
        return redirect(url_for('services.list'))

    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    return render_template('services/edit.html',
                         service=service,
                         categories=categories)


@bp.route('/<int:service_id>/delete', methods=['POST'])
@login_required
def delete(service_id):
    service = Service.query.get_or_404(service_id)

    # Vérifier que l'utilisateur peut supprimer ce service
    if service.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce service.', 'danger')
        return redirect(url_for('services.list'))

    service_name = service.name
    db.session.delete(service)
    db.session.commit()

    flash(f'Le service "{service_name}" a été supprimé.', 'success')
    return redirect(url_for('services.list'))


@bp.route('/<int:service_id>/plans')
@login_required
def plans(service_id):
    service = Service.query.get_or_404(service_id)

    # Vérifier les permissions
    if service.is_custom() and service.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce service.', 'danger')
        return redirect(url_for('services.list'))

    # Séparer les plans globaux et les plans personnalisés
    global_plans = [p for p in service.plans if not p.is_custom()]
    custom_plans = [p for p in service.plans if p.is_custom() and p.user_id == current_user.id]

    return render_template('services/plans.html',
                         service=service,
                         global_plans=global_plans,
                         custom_plans=custom_plans)


@bp.route('/<int:service_id>/plans/add', methods=['GET', 'POST'])
@login_required
def add_plan(service_id):
    service = Service.query.get_or_404(service_id)

    # Vérifier les permissions pour les services personnalisés
    if service.is_custom() and service.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce service.', 'danger')
        return redirect(url_for('services.list'))

    # Vérifier que l'utilisateur peut créer un plan personnalisé
    if not current_user.can_create_custom_plan():
        if current_user.is_premium():
            flash('Vous avez atteint la limite de plans personnalisés.', 'warning')
        else:
            count = current_user.get_custom_plans_count()
            flash(f'Vous avez atteint la limite de 10 plans personnalisés pour le plan gratuit ({count}/10). Passez au plan Premium pour créer un nombre illimité de plans.', 'warning')
        return redirect(url_for('services.plans', service_id=service.id))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        amount = float(request.form.get('amount'))
        currency = request.form.get('currency', 'EUR')
        billing_cycle = request.form.get('billing_cycle')

        # Déterminer si c'est un plan personnalisé
        # Un plan est personnalisé si le service est global (user_id=None)
        # ou si le service est personnalisé de l'utilisateur
        user_id = None if service.user_id is None else current_user.id
        if service.user_id is None:
            # Pour les services globaux, toujours créer un plan personnalisé
            user_id = current_user.id

        plan = ServicePlan(
            service_id=service.id,
            user_id=user_id,
            name=name,
            description=description,
            amount=amount,
            currency=currency,
            billing_cycle=billing_cycle
        )

        db.session.add(plan)
        db.session.commit()

        flash(f'La formule "{name}" a été ajoutée au service "{service.name}".', 'success')
        return redirect(url_for('services.plans', service_id=service.id))

    return render_template('services/add_plan.html', service=service)


@bp.route('/plans/<int:plan_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_plan(plan_id):
    plan = ServicePlan.query.get_or_404(plan_id)
    service = plan.service

    # Vérifier les permissions
    # L'utilisateur peut modifier :
    # - Les plans de ses services personnalisés
    # - Ses propres plans personnalisés (user_id = current_user.id)
    can_edit = False

    if service.is_custom() and service.user_id == current_user.id:
        can_edit = True
    elif plan.is_custom() and plan.user_id == current_user.id:
        can_edit = True

    if not can_edit:
        flash('Vous n\'avez pas l\'autorisation de modifier cette formule.', 'danger')
        return redirect(url_for('services.plans', service_id=service.id))

    if request.method == 'POST':
        plan.name = request.form.get('name')
        plan.description = request.form.get('description')
        plan.amount = float(request.form.get('amount'))
        plan.currency = request.form.get('currency', 'EUR')
        plan.billing_cycle = request.form.get('billing_cycle')

        db.session.commit()

        flash(f'La formule "{plan.name}" a été mise à jour.', 'success')
        return redirect(url_for('services.plans', service_id=service.id))

    return render_template('services/edit_plan.html', plan=plan, service=service)


@bp.route('/plans/<int:plan_id>/delete', methods=['POST'])
@login_required
def delete_plan(plan_id):
    plan = ServicePlan.query.get_or_404(plan_id)
    service = plan.service

    # Vérifier les permissions
    # L'utilisateur peut supprimer :
    # - Les plans de ses services personnalisés
    # - Ses propres plans personnalisés (user_id = current_user.id)
    can_delete = False

    if service.is_custom() and service.user_id == current_user.id:
        can_delete = True
    elif plan.is_custom() and plan.user_id == current_user.id:
        can_delete = True

    if not can_delete:
        flash('Vous n\'avez pas l\'autorisation de supprimer cette formule.', 'danger')
        return redirect(url_for('services.plans', service_id=service.id))

    plan_name = plan.name
    service_id = service.id
    db.session.delete(plan)
    db.session.commit()

    flash(f'La formule "{plan_name}" a été supprimée.', 'success')
    return redirect(url_for('services.plans', service_id=service_id))


@bp.route('/<int:service_id>/customize', methods=['POST'])
@login_required
def customize(service_id):
    """Dupliquer un service global pour le personnaliser"""
    # Vérifier que l'utilisateur est Premium
    if not current_user.is_premium():
        flash('La personnalisation des services est réservée aux utilisateurs Premium.', 'warning')
        return redirect(url_for('main.pricing'))

    # Récupérer le service global
    global_service = Service.query.get_or_404(service_id)

    # Vérifier que c'est bien un service global
    if not global_service.is_global():
        flash('Seuls les services par défaut peuvent être personnalisés.', 'danger')
        return redirect(url_for('services.list'))

    # Vérifier si l'utilisateur a déjà un service avec ce nom
    existing = Service.query.filter_by(user_id=current_user.id, name=global_service.name).first()
    if existing:
        flash(f'Vous avez déjà un service nommé "{global_service.name}". Modifiez-le directement.', 'warning')
        return redirect(url_for('services.edit', service_id=existing.id))

    # Créer une copie personnalisée du service
    custom_service = Service(
        user_id=current_user.id,
        category_id=global_service.category_id,
        name=global_service.name,
        description=global_service.description,
        logo_data=global_service.logo_data,
        logo_mime_type=global_service.logo_mime_type,
        website_url=global_service.website_url,
        is_active=True
    )

    db.session.add(custom_service)
    db.session.flush()  # Pour obtenir l'ID du nouveau service

    # Copier tous les plans du service global
    for global_plan in global_service.plans:
        custom_plan = ServicePlan(
            service_id=custom_service.id,
            user_id=current_user.id,
            name=global_plan.name,
            description=global_plan.description,
            amount=global_plan.amount,
            currency=global_plan.currency,
            billing_cycle=global_plan.billing_cycle,
            is_active=global_plan.is_active
        )
        db.session.add(custom_plan)

    db.session.commit()

    flash(f'Le service "{global_service.name}" et ses formules ont été dupliqués. Vous pouvez maintenant les personnaliser.', 'success')
    return redirect(url_for('services.edit', service_id=custom_service.id))


@bp.route('/<int:service_id>/hide', methods=['POST'])
@login_required
def hide(service_id):
    """Masquer un service global"""
    # Vérifier que l'utilisateur est Premium
    if not current_user.is_premium():
        flash('Le masquage des services est réservé aux utilisateurs Premium.', 'warning')
        return redirect(url_for('main.pricing'))

    # Récupérer le service
    service = Service.query.get_or_404(service_id)

    # Vérifier que c'est bien un service global
    if not service.is_global():
        flash('Seuls les services par défaut peuvent être masqués.', 'danger')
        return redirect(url_for('services.list'))

    # Ajouter à la liste des services masqués
    if service not in current_user.hidden_services_list:
        current_user.hidden_services_list.append(service)
        db.session.commit()
        flash(f'Le service "{service.name}" a été masqué.', 'success')
    else:
        flash(f'Le service "{service.name}" est déjà masqué.', 'info')

    return redirect(url_for('services.list'))


@bp.route('/<int:service_id>/unhide', methods=['POST'])
@login_required
def unhide(service_id):
    """Afficher un service global masqué"""
    # Vérifier que l'utilisateur est Premium
    if not current_user.is_premium():
        flash('La gestion des services masqués est réservée aux utilisateurs Premium.', 'warning')
        return redirect(url_for('main.pricing'))

    # Récupérer le service
    service = Service.query.get_or_404(service_id)

    # Retirer de la liste des services masqués
    if service in current_user.hidden_services_list:
        current_user.hidden_services_list.remove(service)
        db.session.commit()
        flash(f'Le service "{service.name}" est de nouveau visible.', 'success')
    else:
        flash(f'Le service "{service.name}" n\'était pas masqué.', 'info')

    return redirect(url_for('services.list'))
