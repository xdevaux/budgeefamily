from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Subscription, Category, Plan, Notification
from datetime import datetime, timedelta
from sqlalchemy import func
import stripe
import os

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')


@bp.route('/dashboard')
@login_required
def dashboard():
    # Statistiques
    active_subscriptions = current_user.subscriptions.filter_by(is_active=True).all()
    total_monthly_cost = sum(
        sub.amount if sub.billing_cycle == 'monthly' else
        sub.amount / 3 if sub.billing_cycle == 'quarterly' else
        sub.amount / 12 if sub.billing_cycle == 'yearly' else
        sub.amount * 4 if sub.billing_cycle == 'weekly' else 0
        for sub in active_subscriptions
    )

    # Prochains renouvellements - tous les abonnements actifs triés par date
    upcoming_renewals = current_user.subscriptions.filter(
        Subscription.is_active == True
    ).order_by(Subscription.next_billing_date).all()

    # Répartition par catégorie
    category_stats = db.session.query(
        Category.name,
        Category.color,
        func.count(Subscription.id).label('count'),
        func.sum(Subscription.amount).label('total')
    ).join(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    ).group_by(Category.id).all()

    # Notifications non lues
    unread_notifications = current_user.notifications.filter_by(is_read=False).count()

    return render_template('dashboard.html',
                         active_subscriptions=active_subscriptions,
                         total_monthly_cost=round(total_monthly_cost, 2),
                         upcoming_renewals=upcoming_renewals,
                         category_stats=category_stats,
                         unread_notifications=unread_notifications,
                         now=datetime.utcnow())


@bp.route('/pricing')
def pricing():
    plans = Plan.query.filter_by(is_active=True).order_by(Plan.price).all()
    return render_template('pricing.html', plans=plans)


@bp.route('/notifications')
@login_required
def notifications():
    user_notifications = current_user.notifications.order_by(
        Notification.created_at.desc()
    ).all()
    return render_template('notifications.html', notifications=user_notifications)


@bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        return redirect(url_for('main.notifications'))

    notification.mark_as_read()
    return redirect(url_for('main.notifications'))


@bp.route('/checkout-redirect')
@login_required
def checkout_redirect():
    """Redirige vers Stripe Checkout pour finaliser un paiement Premium"""
    plan_type = request.args.get('plan', 'monthly')  # 'monthly' ou 'yearly'

    try:
        # Initialiser Stripe
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

        # Sélectionner le bon plan
        if plan_type == 'yearly':
            plan_name = 'Premium Annual'
        else:
            plan_name = 'Premium'

        premium_plan = Plan.query.filter_by(name=plan_name).first()
        if not premium_plan or not premium_plan.stripe_price_id:
            flash(f'Plan {plan_name} non configuré. Veuillez contacter le support.', 'danger')
            return redirect(url_for('main.pricing'))

        # Créer la session Stripe Checkout
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[{
                'price': premium_plan.stripe_price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('api.checkout_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('main.pricing', _external=True),
            metadata={
                'user_id': current_user.id,
                'plan_type': plan_type
            }
        )

        return redirect(checkout_session.url)

    except Exception as e:
        current_app.logger.error(f'Erreur lors de la création de la session Stripe: {str(e)}')
        flash('Erreur lors de la redirection vers le paiement. Veuillez réessayer.', 'danger')
        return redirect(url_for('main.pricing'))
