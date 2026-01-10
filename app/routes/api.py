from flask import Blueprint, request, jsonify, current_app, redirect, url_for, make_response
from flask_login import login_required, current_user
from app import db
from app.models import User, Plan, Notification, Subscription, Category, Service
import stripe
import os
import base64

bp = Blueprint('api', __name__, url_prefix='/api')


def init_stripe():
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')


@bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    try:
        init_stripe()

        # Récupérer le plan demandé (monthly par défaut, ou yearly)
        data = request.get_json() or {}
        plan_type = data.get('plan', 'monthly')  # 'monthly' ou 'yearly'

        # Sélectionner le bon plan
        if plan_type == 'yearly':
            plan_name = 'Premium Annual'
        else:
            plan_name = 'Premium'

        premium_plan = Plan.query.filter_by(name=plan_name).first()
        if not premium_plan or not premium_plan.stripe_price_id:
            return jsonify({'error': f'Plan {plan_name} non configuré'}), 400

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

        return jsonify({'checkout_url': checkout_session.url})

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/checkout/success')
@login_required
def checkout_success():
    session_id = request.args.get('session_id')

    if session_id:
        try:
            init_stripe()
            session = stripe.checkout.Session.retrieve(session_id)

            if session.payment_status == 'paid':
                # Mettre à jour le plan de l'utilisateur
                premium_plan = Plan.query.filter_by(name='Premium').first()
                current_user.plan_id = premium_plan.id
                current_user.stripe_customer_id = session.customer
                current_user.stripe_subscription_id = session.subscription

                # Créer une notification
                notification = Notification(
                    user_id=current_user.id,
                    type='upgrade',
                    title='Bienvenue sur le plan Premium !',
                    message='Votre abonnement Premium a été activé. Vous pouvez maintenant ajouter un nombre illimité d\'abonnements.'
                )
                db.session.add(notification)
                db.session.commit()

                # Envoyer l'email de confirmation
                from app.utils.email import send_plan_upgrade_email
                send_plan_upgrade_email(current_user, premium_plan.name)

                # Récupérer et envoyer la facture
                try:
                    subscription_obj = stripe.Subscription.retrieve(session.subscription)
                    if subscription_obj.latest_invoice:
                        from app.utils.email import send_invoice_email
                        send_invoice_email(current_user, subscription_obj.latest_invoice)
                except Exception as e:
                    current_app.logger.error(f'Erreur lors de l\'envoi de la facture: {str(e)}')

                return redirect(url_for('main.dashboard'))

        except Exception as e:
            current_app.logger.error(f'Erreur lors de la vérification du paiement: {str(e)}')

    return redirect(url_for('main.pricing'))


@bp.route('/create-portal-session', methods=['POST'])
@login_required
def create_portal_session():
    try:
        init_stripe()

        if not current_user.stripe_customer_id:
            return jsonify({'error': 'Aucun abonnement Stripe trouvé'}), 400

        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=url_for('auth.profile', _external=True)
        )

        return jsonify({'portal_url': portal_session.url})

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400

    # Gérer les événements Stripe
    if event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)

    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)

    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        handle_invoice_payment_succeeded(invoice)

    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        handle_payment_failed(invoice)

    return jsonify({'status': 'success'}), 200


def handle_subscription_updated(stripe_subscription):
    user = User.query.filter_by(stripe_subscription_id=stripe_subscription['id']).first()
    if user:
        if stripe_subscription['status'] == 'active':
            # Vérifier si c'est un upgrade (l'utilisateur n'était pas Premium avant)
            was_premium = user.plan and user.plan.is_premium()

            premium_plan = Plan.query.filter_by(name='Premium').first()
            user.plan_id = premium_plan.id

            # Créer une notification uniquement si c'est un nouveau passage à Premium
            if not was_premium:
                notification = Notification(
                    user_id=user.id,
                    type='upgrade',
                    title='Bienvenue sur le plan Premium !',
                    message='Votre abonnement Premium a été activé. Vous pouvez maintenant ajouter un nombre illimité d\'abonnements.'
                )
                db.session.add(notification)

            db.session.commit()

            # Envoyer l'email de confirmation uniquement si c'est un nouveau passage à Premium
            if not was_premium:
                from app.utils.email import send_plan_upgrade_email
                send_plan_upgrade_email(user, premium_plan.name)


def handle_subscription_deleted(stripe_subscription):
    user = User.query.filter_by(stripe_subscription_id=stripe_subscription['id']).first()
    if user:
        # Sauvegarder le nom de l'ancien plan pour l'email
        old_plan_name = user.plan.name if user.plan else 'Premium'

        free_plan = Plan.query.filter_by(name='Free').first()
        user.plan_id = free_plan.id
        user.stripe_subscription_id = None

        # Créer une notification
        notification = Notification(
            user_id=user.id,
            type='downgrade',
            title='Abonnement Premium annulé',
            message='Votre abonnement Premium a été annulé. Vous êtes maintenant sur le plan gratuit.'
        )
        db.session.add(notification)
        db.session.commit()

        # Envoyer l'email de confirmation de rétrogradation
        from app.utils.email import send_plan_downgrade_email
        send_plan_downgrade_email(user, old_plan_name)


def handle_payment_failed(invoice):
    customer_id = invoice['customer']
    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if user:
        notification = Notification(
            user_id=user.id,
            type='payment_failed',
            title='Échec de paiement',
            message='Le paiement de votre abonnement Premium a échoué. Veuillez mettre à jour vos informations de paiement.'
        )
        db.session.add(notification)
        db.session.commit()


def handle_invoice_payment_succeeded(invoice):
    """Envoie la facture par email lorsqu'un paiement réussit"""
    customer_id = invoice['customer']
    user = User.query.filter_by(stripe_customer_id=customer_id).first()

    if user:
        # Envoyer la facture par email
        try:
            from app.utils.email import send_invoice_email
            send_invoice_email(user, invoice['id'])
        except Exception as e:
            print(f"Erreur lors de l'envoi de la facture par email : {e}")


@bp.route('/logo/<string:entity_type>/<int:entity_id>')
def serve_logo(entity_type, entity_id):
    """Sert les logos depuis la base de données"""
    try:
        # Récupérer l'entité (service ou category)
        if entity_type == 'service':
            entity = Service.query.get_or_404(entity_id)
        elif entity_type == 'category':
            entity = Category.query.get_or_404(entity_id)
        else:
            return jsonify({'error': 'Type invalide'}), 400

        # Vérifier si le logo existe
        if not entity.logo_data or not entity.logo_mime_type:
            return jsonify({'error': 'Logo non trouvé'}), 404

        # Décoder le base64
        logo_bytes = base64.b64decode(entity.logo_data)

        # Créer la réponse avec le bon MIME type
        response = make_response(logo_bytes)
        response.headers.set('Content-Type', entity.logo_mime_type)
        response.headers.set('Cache-Control', 'public, max-age=86400')  # Cache 24h

        return response

    except Exception as e:
        current_app.logger.error(f'Erreur lors du chargement du logo: {str(e)}')
        return jsonify({'error': 'Erreur serveur'}), 500


@bp.route('/stats')
@login_required
def stats():
    """API endpoint pour récupérer les statistiques"""
    from datetime import datetime, timedelta
    from sqlalchemy import func

    # Traduction des mois en français
    MONTHS_FR = {
        1: 'Jan', 2: 'Fév', 3: 'Mar', 4: 'Avr', 5: 'Mai', 6: 'Juin',
        7: 'Juil', 8: 'Août', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Déc'
    }

    # Dépenses des 12 derniers mois
    monthly_stats = []
    for i in range(12):
        month_date = datetime.utcnow() - timedelta(days=30 * i)
        month_start = month_date.replace(day=1)

        subscriptions = current_user.subscriptions.filter(
            db.and_(
                Subscription.is_active == True,
                Subscription.start_date <= month_start.date()
            )
        ).all()

        monthly_total = sum(
            sub.amount if sub.billing_cycle == 'monthly' else
            sub.amount / 3 if sub.billing_cycle == 'quarterly' else
            sub.amount / 12 if sub.billing_cycle == 'yearly' else
            sub.amount * 4 if sub.billing_cycle == 'weekly' else 0
            for sub in subscriptions
        )

        monthly_stats.insert(0, {
            'month': f"{MONTHS_FR[month_start.month]} {month_start.year}",
            'total': round(monthly_total, 2)
        })

    return jsonify({
        'monthly_spending': monthly_stats,
        'total_subscriptions': current_user.get_active_subscriptions_count(),
        'plan': current_user.plan.name if current_user.plan else 'Free'
    })
