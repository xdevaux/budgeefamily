from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Subscription, Category, Plan, Notification, Credit, Revenue
from datetime import datetime, timedelta
from sqlalchemy import func, case
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

    # Calculer le total mensuel des abonnements actifs uniquement
    total_subscriptions_cost = sum(
        sub.amount if sub.billing_cycle == 'monthly' else
        sub.amount / 3 if sub.billing_cycle == 'quarterly' else
        sub.amount / 12 if sub.billing_cycle == 'yearly' else
        sub.amount * 4 if sub.billing_cycle == 'weekly' else 0
        for sub in active_subscriptions
    )

    # Calculer le coût mensuel total (abonnements + crédits + revenus, etc.)
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

    # Prochains débits pour les crédits - tous les crédits actifs triés par date
    upcoming_credits = current_user.credits.filter(
        Credit.is_active == True
    ).order_by(Credit.next_payment_date).all()

    # Prochains versements pour les revenus - tous les revenus actifs triés par date
    upcoming_revenues = current_user.revenues.filter(
        Revenue.is_active == True
    ).order_by(Revenue.next_payment_date).all()

    # Répartition par catégorie (abonnements + crédits)
    category_stats = db.session.query(
        Category.name,
        Category.color,
        func.count(Subscription.id).label('subscription_count'),
        func.sum(Subscription.amount).label('subscription_total'),
        func.count(Credit.id).label('credit_count'),
        func.sum(Credit.amount).label('credit_total'),
        (func.coalesce(func.sum(Subscription.amount), 0) + func.coalesce(func.sum(Credit.amount), 0)).label('total')
    ).outerjoin(Subscription,
        (Subscription.category_id == Category.id) &
        (Subscription.user_id == current_user.id) &
        (Subscription.is_active == True)
    ).outerjoin(Credit,
        (Credit.category_id == Category.id) &
        (Credit.user_id == current_user.id) &
        (Credit.is_active == True)
    ).filter(
        (Subscription.id != None) | (Credit.id != None)
    ).group_by(Category.id).all()

    # Calculer le total des crédits actifs pour la catégorie "Crédits"
    total_credits = sum(
        credit.amount if credit.billing_cycle == 'monthly' else
        credit.amount / 3 if credit.billing_cycle == 'quarterly' else
        credit.amount / 12 if credit.billing_cycle == 'yearly' else 0
        for credit in upcoming_credits
    )

    # Répartition des revenus par employeur
    revenue_data = {}
    colors_palette = ['#10b981', '#22c55e', '#34d399', '#6ee7b7', '#a7f3d0', '#d1fae5']

    for revenue in upcoming_revenues:
        if revenue.employer:
            employer_name = revenue.employer.name
        else:
            employer_name = 'Autres revenus'

        monthly_amount = revenue.amount

        # Convertir en montant mensuel selon le cycle
        if revenue.billing_cycle == 'yearly':
            monthly_amount = revenue.amount / 12
        elif revenue.billing_cycle == 'quarterly':
            monthly_amount = revenue.amount / 3

        if employer_name not in revenue_data:
            revenue_data[employer_name] = {
                'name': employer_name,
                'total': 0,
                'color': colors_palette[len(revenue_data) % len(colors_palette)]
            }

        revenue_data[employer_name]['total'] += monthly_amount

    revenue_stats = sorted(revenue_data.values(), key=lambda x: x['total'], reverse=True)

    # Calculer le total des revenus mensuels
    total_revenues = sum(
        revenue.amount if revenue.billing_cycle == 'monthly' else
        revenue.amount / 3 if revenue.billing_cycle == 'quarterly' else
        revenue.amount / 12 if revenue.billing_cycle == 'yearly' else 0
        for revenue in upcoming_revenues
    )

    # Calculer le solde : revenus - (abonnements + crédits)
    solde = total_revenues - (total_subscriptions_cost + total_credits)

    # Notifications non lues
    unread_notifications = current_user.notifications.filter_by(is_read=False).count()

    return render_template('dashboard.html',
                         active_subscriptions=active_subscriptions,
                         total_subscriptions_cost=round(total_subscriptions_cost, 2),
                         total_monthly_cost=round(total_monthly_cost, 2),
                         upcoming_renewals=upcoming_renewals,
                         upcoming_credits=upcoming_credits,
                         upcoming_revenues=upcoming_revenues,
                         category_stats=category_stats,
                         revenue_stats=revenue_stats,
                         total_credits=round(total_credits, 2),
                         total_revenues=round(total_revenues, 2),
                         solde=round(solde, 2),
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


@bp.route('/mentions-legales')
def mentions_legales():
    """Page des mentions légales du site"""
    return render_template('mentions_legales.html')


@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Page de contact avec formulaire"""
    if request.method == 'POST':
        # Protection anti-spam : vérifier le champ honeypot
        honeypot = request.form.get('website', '').strip()
        if honeypot:
            # Un robot a rempli le champ invisible - rejeter silencieusement
            current_app.logger.warning(f'Tentative de spam détectée (honeypot rempli): {request.remote_addr}')
            flash('Votre message a été envoyé avec succès ! Nous vous répondrons dans les plus brefs délais.', 'success')
            return redirect(url_for('main.contact'))

        # Protection anti-spam : vérifier le timestamp (soumission trop rapide)
        timestamp = request.form.get('timestamp', '0')
        try:
            timestamp_ms = int(timestamp)
            time_elapsed = (datetime.now().timestamp() * 1000) - timestamp_ms
            if time_elapsed < 3000:  # Moins de 3 secondes
                current_app.logger.warning(f'Tentative de spam détectée (soumission trop rapide): {request.remote_addr}')
                flash('Votre message a été envoyé avec succès ! Nous vous répondrons dans les plus brefs délais.', 'success')
                return redirect(url_for('main.contact'))
        except (ValueError, TypeError):
            # Timestamp invalide ou absent
            current_app.logger.warning(f'Tentative de spam détectée (timestamp invalide): {request.remote_addr}')
            flash('Votre message a été envoyé avec succès ! Nous vous répondrons dans les plus brefs délais.', 'success')
            return redirect(url_for('main.contact'))

        # Récupérer les données du formulaire
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        # Validation
        if not email:
            flash('Veuillez saisir votre adresse email.', 'danger')
            return render_template('contact.html', name=name, subject=subject, message=message)

        if not name:
            flash('Veuillez saisir votre nom.', 'danger')
            return render_template('contact.html', email=email, subject=subject, message=message)

        if not message:
            flash('Veuillez saisir votre message.', 'danger')
            return render_template('contact.html', name=name, email=email, subject=subject)

        # Validation basique de l'email
        if '@' not in email or '.' not in email:
            flash('Veuillez saisir une adresse email valide.', 'danger')
            return render_template('contact.html', name=name, subject=subject, message=message)

        # Envoi de l'email
        try:
            from flask_mail import Message
            from app import mail

            msg = Message(
                subject=f"[Contact Budgee Family] {subject or 'Sans objet'}",
                sender=current_app.config['MAIL_DEFAULT_SENDER'],
                recipients=['contact@budgeefamily.com'],
                reply_to=email
            )

            msg.body = f"""
Nouveau message de contact reçu sur Budgee Family

Nom: {name}
Email: {email}
Objet: {subject or 'Non spécifié'}

Message:
{message}

---
Envoyé depuis le formulaire de contact de Budgee Family
"""

            msg.html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fa; border-radius: 10px;">
        <h2 style="color: #6366f1; border-bottom: 3px solid #6366f1; padding-bottom: 10px;">
            Nouveau message de contact
        </h2>

        <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p><strong>Nom:</strong> {name}</p>
            <p><strong>Email:</strong> <a href="mailto:{email}">{email}</a></p>
            <p><strong>Objet:</strong> {subject or 'Non spécifié'}</p>

            <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #6366f1; border-radius: 4px;">
                <strong>Message:</strong>
                <p style="white-space: pre-wrap; margin-top: 10px;">{message}</p>
            </div>
        </div>

        <p style="text-align: center; color: #666; font-size: 12px; margin-top: 20px;">
            Envoyé depuis le formulaire de contact de Budgee Family
        </p>
    </div>
</body>
</html>
"""

            mail.send(msg)

            # Envoyer un email de confirmation au visiteur
            try:
                from app.utils.email import send_contact_confirmation_email
                send_contact_confirmation_email(name, email)
            except Exception as conf_error:
                current_app.logger.error(f"Erreur lors de l'envoi de l'email de confirmation: {str(conf_error)}")
                # Ne pas bloquer le processus si l'email de confirmation échoue

            flash('Votre message a été envoyé avec succès ! Nous vous répondrons dans les plus brefs délais.', 'success')
            return redirect(url_for('main.contact'))

        except Exception as e:
            current_app.logger.error(f"Erreur lors de l'envoi de l'email de contact: {str(e)}")
            flash('Une erreur est survenue lors de l\'envoi de votre message. Veuillez réessayer plus tard.', 'danger')
            return render_template('contact.html', name=name, email=email, subject=subject, message=message)

    return render_template('contact.html')
