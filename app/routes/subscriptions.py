from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Subscription, Category, Notification, Service
from datetime import datetime, timedelta

bp = Blueprint('subscriptions', __name__, url_prefix='/subscriptions')


def get_user_categories():
    """Récupère les catégories globales et personnalisées de l'utilisateur actuel"""
    # Catégories globales (par défaut)
    global_categories = Category.query.filter_by(user_id=None, is_active=True).order_by(Category.name).all()

    # Catégories personnalisées de l'utilisateur
    custom_categories = current_user.custom_categories.filter_by(is_active=True).order_by(Category.name).all()

    # Combiner les deux listes
    return global_categories + custom_categories


def get_user_services():
    """Récupère les services globaux et personnalisés de l'utilisateur actuel avec plans sérialisables"""
    # Services globaux (par défaut)
    global_services = Service.query.filter_by(user_id=None, is_active=True).order_by(Service.name).all()

    # Services personnalisés de l'utilisateur
    custom_services = Service.query.filter_by(user_id=current_user.id, is_active=True).order_by(Service.name).all()

    # Combiner les deux listes
    all_services = global_services + custom_services

    # Préparer les données pour le template (rendre les plans sérialisables)
    services_data = []
    for service in all_services:
        service_dict = {
            'id': service.id,
            'name': service.name,
            'category_id': service.category_id,
            'plans': [plan.to_dict() for plan in service.plans if plan.is_active]
        }
        services_data.append(service_dict)

    return services_data


@bp.route('/')
@login_required
def list():
    page = request.args.get('page', 1, type=int)
    filter_status = request.args.get('status', 'all')
    filter_category = request.args.get('category', None, type=int)

    query = current_user.subscriptions

    if filter_status == 'active':
        query = query.filter_by(is_active=True)
    elif filter_status == 'inactive':
        query = query.filter_by(is_active=False)

    if filter_category:
        query = query.filter_by(category_id=filter_category)

    subscriptions = query.order_by(Subscription.next_billing_date).paginate(
        page=page, per_page=10, error_out=False
    )

    categories = get_user_categories()

    return render_template('subscriptions/list.html',
                         subscriptions=subscriptions,
                         categories=categories,
                         filter_status=filter_status,
                         filter_category=filter_category)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if not current_user.can_add_subscription():
        flash('Vous avez atteint la limite de votre plan. Passez au plan Premium pour ajouter plus d\'abonnements.', 'warning')
        return redirect(url_for('main.pricing'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        amount = float(request.form.get('amount'))
        currency = request.form.get('currency', 'EUR')
        billing_cycle = request.form.get('billing_cycle')
        category_id = request.form.get('category_id', type=int)
        service_id = request.form.get('service_id', type=int)
        plan_id = request.form.get('plan_id', type=int)
        start_date_str = request.form.get('start_date')

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

        subscription = Subscription(
            user_id=current_user.id,
            name=name,
            description=description,
            amount=amount,
            currency=currency,
            billing_cycle=billing_cycle,
            category_id=category_id if category_id else None,
            service_id=service_id if service_id else None,
            plan_id=plan_id if plan_id else None,
            start_date=start_date,
            next_billing_date=start_date
        )

        # Calculer la prochaine date de facturation
        if billing_cycle == 'monthly':
            subscription.next_billing_date = start_date + timedelta(days=30)
        elif billing_cycle == 'quarterly':
            subscription.next_billing_date = start_date + timedelta(days=90)
        elif billing_cycle == 'yearly':
            subscription.next_billing_date = start_date + timedelta(days=365)
        elif billing_cycle == 'weekly':
            subscription.next_billing_date = start_date + timedelta(days=7)

        db.session.add(subscription)
        db.session.commit()

        # Créer une notification
        notification = Notification(
            user_id=current_user.id,
            subscription_id=subscription.id,
            type='subscription_added',
            title='Nouvel abonnement ajouté',
            message=f'Votre abonnement "{name}" a été ajouté avec succès.'
        )
        db.session.add(notification)
        db.session.commit()

        flash(f'L\'abonnement "{name}" a été ajouté avec succès !', 'success')
        return redirect(url_for('subscriptions.list'))

    categories = get_user_categories()
    services = get_user_services()
    return render_template('subscriptions/add.html', categories=categories, services=services)


@bp.route('/<int:subscription_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(subscription_id):
    subscription = Subscription.query.get_or_404(subscription_id)

    if subscription.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cet abonnement.', 'danger')
        return redirect(url_for('subscriptions.list'))

    if request.method == 'POST':
        subscription.name = request.form.get('name')
        subscription.description = request.form.get('description')
        subscription.amount = float(request.form.get('amount'))
        subscription.currency = request.form.get('currency', 'EUR')
        subscription.billing_cycle = request.form.get('billing_cycle')
        subscription.category_id = request.form.get('category_id', type=int) or None
        subscription.service_id = request.form.get('service_id', type=int) or None
        subscription.plan_id = request.form.get('plan_id', type=int) or None

        db.session.commit()

        flash(f'L\'abonnement "{subscription.name}" a été mis à jour.', 'success')
        return redirect(url_for('subscriptions.list'))

    categories = get_user_categories()
    services = get_user_services()
    return render_template('subscriptions/edit.html',
                         subscription=subscription,
                         categories=categories,
                         services=services)


@bp.route('/<int:subscription_id>/delete', methods=['POST'])
@login_required
def delete(subscription_id):
    subscription = Subscription.query.get_or_404(subscription_id)

    if subscription.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cet abonnement.', 'danger')
        return redirect(url_for('subscriptions.list'))

    subscription_name = subscription.name
    db.session.delete(subscription)
    db.session.commit()

    flash(f'L\'abonnement "{subscription_name}" a été supprimé.', 'success')
    return redirect(url_for('subscriptions.list'))


@bp.route('/<int:subscription_id>/toggle', methods=['POST'])
@login_required
def toggle(subscription_id):
    subscription = Subscription.query.get_or_404(subscription_id)

    if subscription.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cet abonnement.', 'danger')
        return redirect(url_for('subscriptions.list'))

    subscription.is_active = not subscription.is_active
    if not subscription.is_active:
        subscription.cancelled_at = datetime.utcnow()
    else:
        subscription.cancelled_at = None

    db.session.commit()

    status = 'activé' if subscription.is_active else 'désactivé'
    flash(f'L\'abonnement "{subscription.name}" a été {status}.', 'success')
    return redirect(url_for('subscriptions.list'))


@bp.route('/<int:subscription_id>')
@login_required
def detail(subscription_id):
    subscription = Subscription.query.get_or_404(subscription_id)

    if subscription.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cet abonnement.', 'danger')
        return redirect(url_for('subscriptions.list'))

    return render_template('subscriptions/detail.html', subscription=subscription)
