from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app import db
from app.models import Subscription, Category, Notification, Service
from app.utils.transactions import generate_future_transactions, update_future_transactions, cancel_future_transactions, calculate_next_future_date, delete_all_transactions
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

bp = Blueprint('subscriptions', __name__, url_prefix='/subscriptions')


def get_user_categories():
    """Récupère les catégories globales et personnalisées de l'utilisateur actuel"""
    # Catégories globales (par défaut) - uniquement pour abonnements
    global_categories = Category.query.filter_by(
        user_id=None,
        is_active=True
    ).filter(
        db.or_(
            Category.category_type == 'subscription',
            Category.category_type == 'all'
        )
    ).order_by(Category.name).all()

    # Catégories personnalisées de l'utilisateur - uniquement pour abonnements
    custom_categories = current_user.custom_categories.filter_by(
        is_active=True
    ).filter(
        db.or_(
            Category.category_type == 'subscription',
            Category.category_type == 'all'
        )
    ).order_by(Category.name).all()

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
        flash(_('Vous avez atteint la limite d\'abonnements pour le plan gratuit (5/5). Passez au plan Premium pour ajouter des abonnements illimités.'), 'warning')
        return redirect(url_for('subscriptions.list'))

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

        # Calculer la prochaine date de facturation future
        next_billing_date = calculate_next_future_date(start_date, billing_cycle)

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
            next_billing_date=next_billing_date
        )

        db.session.add(subscription)
        db.session.commit()

        # Générer les transactions futures (12 mois)
        generate_future_transactions(subscription, 'subscription', 12)
        db.session.commit()

        # Créer une notification
        notification = Notification(
            user_id=current_user.id,
            subscription_id=subscription.id,
            created_by_user_id=current_user.id,
            type='subscription_added',
            title=_('Nouvel abonnement ajouté'),
            message=_('Votre abonnement "%(name)s" a été ajouté avec succès.', name=name)
        )
        db.session.add(notification)
        db.session.commit()

        # Envoyer un email de notification si activé
        from app.utils.email import send_notification_email
        send_notification_email(current_user, notification)

        flash(_('L\'abonnement "%(name)s" a été ajouté avec succès !', name=name), 'success')
        return redirect(url_for('subscriptions.list'))

    categories = get_user_categories()
    services = get_user_services()
    return render_template('subscriptions/add.html', categories=categories, services=services)


@bp.route('/<int:subscription_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(subscription_id):
    subscription = Subscription.query.get_or_404(subscription_id)

    if subscription.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à cet abonnement.'), 'danger')
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

        # Recalculer la prochaine date de facturation future basée sur la start_date et le nouveau billing_cycle
        subscription.next_billing_date = calculate_next_future_date(subscription.start_date, subscription.billing_cycle)

        db.session.commit()

        # Mettre à jour les transactions futures
        update_future_transactions(subscription, 'subscription')
        db.session.commit()

        flash(_('L\'abonnement "%(name)s" a été mis à jour.', name=subscription.name), 'success')
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
        flash(_('Vous n\'avez pas accès à cet abonnement.'), 'danger')
        return redirect(url_for('subscriptions.list'))

    subscription_name = subscription.name

    # Supprimer toutes les transactions associées
    delete_all_transactions(subscription.id, 'subscription')

    db.session.delete(subscription)
    db.session.commit()

    flash(_('L\'abonnement "%(name)s" et toutes ses transactions ont été supprimés.', name=subscription_name), 'success')

    # Rediriger vers la page balance si le paramètre est présent
    redirect_to = request.args.get('redirect_to', 'subscriptions.list')
    if redirect_to == 'balance':
        return redirect(url_for('main.balance'))
    return redirect(url_for('subscriptions.list'))


@bp.route('/<int:subscription_id>/toggle', methods=['POST'])
@login_required
def toggle(subscription_id):
    subscription = Subscription.query.get_or_404(subscription_id)

    if subscription.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à cet abonnement.'), 'danger')
        return redirect(url_for('subscriptions.list'))

    subscription.is_active = not subscription.is_active
    if not subscription.is_active:
        subscription.cancelled_at = datetime.utcnow()
        # Annuler les transactions futures
        cancel_future_transactions(subscription.id, 'subscription')
    else:
        subscription.cancelled_at = None
        # Régénérer les transactions futures
        generate_future_transactions(subscription, 'subscription', 12)

    db.session.commit()

    status = _('activé') if subscription.is_active else _('désactivé')
    flash(_('L\'abonnement "%(name)s" a été %(status)s.', name=subscription.name, status=status), 'success')
    return redirect(url_for('subscriptions.list'))


@bp.route('/<int:subscription_id>')
@login_required
def detail(subscription_id):
    subscription = Subscription.query.get_or_404(subscription_id)

    if subscription.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à cet abonnement.'), 'danger')
        return redirect(url_for('subscriptions.list'))

    return render_template('subscriptions/detail.html', subscription=subscription)


@bp.route('/<int:subscription_id>/detail-partial')
@login_required
def detail_partial(subscription_id):
    """Retourne un template partiel avec les détails de l'abonnement pour affichage en modale"""
    subscription = Subscription.query.get_or_404(subscription_id)

    if subscription.user_id != current_user.id:
        return '<div class="alert alert-danger">Accès non autorisé</div>', 403

    return render_template('subscriptions/detail_partial.html', subscription=subscription)
