from flask import Blueprint, request, jsonify, current_app, redirect, url_for, make_response
from flask_login import login_required, current_user
from flask_babel import gettext as _
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
        embedded = data.get('embedded', False)  # Mode embedded ou redirect

        # Sélectionner le bon plan
        if plan_type == 'yearly':
            plan_name = 'Premium Annual'
        else:
            plan_name = 'Premium'

        premium_plan = Plan.query.filter_by(name=plan_name).first()
        if not premium_plan or not premium_plan.stripe_price_id:
            return jsonify({'error': f'Plan {plan_name} non configuré'}), 400

        # Configuration commune
        session_config = {
            'customer_email': current_user.email,
            'payment_method_types': ['card'],
            'line_items': [{
                'price': premium_plan.stripe_price_id,
                'quantity': 1,
            }],
            'mode': 'subscription',
            'metadata': {
                'user_id': current_user.id,
                'plan_type': plan_type
            }
        }

        # Mode embedded : intégré dans la page
        if embedded:
            session_config['ui_mode'] = 'embedded'
            session_config['return_url'] = url_for('api.checkout_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}'
        # Mode redirect : redirection vers Stripe
        else:
            session_config['success_url'] = url_for('api.checkout_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}'
            session_config['cancel_url'] = url_for('main.pricing', _external=True)

        checkout_session = stripe.checkout.Session.create(**session_config)

        if embedded:
            # Retourner le client_secret pour le checkout embedded
            return jsonify({'client_secret': checkout_session.client_secret})
        else:
            # Retourner l'URL pour redirection
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
                # Vérifier si c'est un nouvel utilisateur ou un upgrade
                was_premium = current_user.plan and current_user.plan.is_premium()

                # Récupérer le type de plan depuis les métadonnées de la session
                plan_type = session.metadata.get('plan_type', 'monthly')
                if plan_type == 'yearly':
                    plan_name = 'Premium Annual'
                else:
                    plan_name = 'Premium'

                # Mettre à jour le plan de l'utilisateur
                premium_plan = Plan.query.filter_by(name=plan_name).first()
                if not premium_plan:
                    # Fallback sur Premium si le plan n'existe pas
                    premium_plan = Plan.query.filter_by(name='Premium').first()

                current_user.plan_id = premium_plan.id
                current_user.stripe_customer_id = session.customer
                current_user.stripe_subscription_id = session.subscription

                # Créer une notification
                notification = Notification(
                    user_id=current_user.id,
                    type='upgrade',
                    title=f'Bienvenue sur le plan {premium_plan.name} !' if not was_premium else f'Abonnement {premium_plan.name} renouvelé',
                    message=f'Votre abonnement {premium_plan.name} a été activé. Vous pouvez maintenant ajouter un nombre illimité d\'abonnements.'
                )
                db.session.add(notification)
                db.session.commit()

                # Envoyer les emails appropriés selon le contexte
                from app.utils.email import send_plan_upgrade_email, send_welcome_email, send_new_subscription_notification, send_notification_email

                # Envoyer un email de notification si activé
                send_notification_email(current_user, notification)

                if not was_premium:
                    # Nouveau client Premium : envoyer l'email de bienvenue avec récapitulatif
                    send_welcome_email(current_user)
                    # Envoyer la notification à l'équipe
                    send_new_subscription_notification(current_user)
                else:
                    # Upgrade d'un client existant : envoyer l'email d'upgrade
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

            # Déterminer le plan en fonction du price_id de la subscription Stripe
            stripe_price_id = None
            if 'items' in stripe_subscription and 'data' in stripe_subscription['items']:
                items = stripe_subscription['items']['data']
                if items and len(items) > 0:
                    stripe_price_id = items[0]['price']['id']

            # Chercher le plan correspondant au price_id
            premium_plan = None
            if stripe_price_id:
                premium_plan = Plan.query.filter_by(stripe_price_id=stripe_price_id).first()

            # Fallback sur Premium si le plan n'est pas trouvé
            if not premium_plan:
                premium_plan = Plan.query.filter_by(name='Premium').first()

            user.plan_id = premium_plan.id

            # Créer une notification uniquement si c'est un nouveau passage à Premium
            if not was_premium:
                notification = Notification(
                    user_id=user.id,
                    type='upgrade',
                    title=f'Bienvenue sur le plan {premium_plan.name} !',
                    message=f'Votre abonnement {premium_plan.name} a été activé. Vous pouvez maintenant ajouter un nombre illimité d\'abonnements.'
                )
                db.session.add(notification)

            db.session.commit()

            # Envoyer l'email de confirmation uniquement si c'est un nouveau passage à Premium
            if not was_premium:
                from app.utils.email import send_welcome_email, send_new_subscription_notification, send_notification_email
                # Nouveau client Premium : envoyer l'email de bienvenue avec récapitulatif
                send_welcome_email(user)
                # Envoyer la notification à l'équipe
                send_new_subscription_notification(user)
                # Envoyer un email de notification si activé
                send_notification_email(user, notification)


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

        # Envoyer un email de notification si activé
        from app.utils.email import send_plan_downgrade_email, send_notification_email
        send_notification_email(user, notification)

        # Envoyer l'email de confirmation de rétrogradation
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

        # Envoyer un email de notification si activé
        from app.utils.email import send_notification_email
        send_notification_email(user, notification)


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
    from app.models import Credit, Revenue, InstallmentPayment, Check, CardPurchase

    # Traduction des mois en français
    MONTHS_FR = {
        1: 'Jan', 2: 'Fév', 3: 'Mar', 4: 'Avr', 5: 'Mai', 6: 'Juin',
        7: 'Juil', 8: 'Août', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Déc'
    }

    # Initialiser les listes pour les 12 derniers mois
    monthly_subscriptions = []
    monthly_credits_data = []
    monthly_revenues_data = []
    monthly_expenses_data = []

    for i in range(12):
        month_date = datetime.utcnow() - timedelta(days=30 * i)
        month_start = month_date.replace(day=1)
        month_label = f"{MONTHS_FR[month_start.month]} {month_start.year}"

        # Abonnements actifs pour ce mois
        subscriptions = current_user.subscriptions.filter(
            db.and_(
                Subscription.is_active == True,
                Subscription.start_date <= month_start.date()
            )
        ).all()

        subscriptions_total = sum(
            sub.amount if sub.billing_cycle == 'monthly' else
            sub.amount / 3 if sub.billing_cycle == 'quarterly' else
            sub.amount / 12 if sub.billing_cycle == 'yearly' else
            sub.amount * 4 if sub.billing_cycle == 'weekly' else 0
            for sub in subscriptions
        )

        # Crédits actifs pour ce mois
        credits = Credit.query.filter(
            Credit.user_id == current_user.id,
            Credit.is_active == True,
            Credit.start_date <= month_start.date(),
            db.or_(
                Credit.end_date == None,
                Credit.end_date >= month_start.date()
            )
        ).all()

        credits_total = sum(
            credit.amount if credit.billing_cycle == 'monthly' else
            credit.amount / 3 if credit.billing_cycle == 'quarterly' else
            credit.amount / 12 if credit.billing_cycle == 'yearly' else 0
            for credit in credits
        )

        # Paiements en plusieurs fois actifs pour ce mois
        installments = InstallmentPayment.query.filter(
            InstallmentPayment.user_id == current_user.id,
            InstallmentPayment.is_active == True,
            InstallmentPayment.start_date <= month_start.date(),
            db.or_(
                InstallmentPayment.is_completed == False,
                db.and_(
                    InstallmentPayment.is_completed == True,
                    InstallmentPayment.completed_at >= month_start
                )
            )
        ).all()

        installments_total = sum(
            installment.installment_amount
            for installment in installments
        )

        # Ajouter les paiements en plusieurs fois aux crédits
        credits_total += installments_total

        # Revenus actifs pour ce mois
        revenues = Revenue.query.filter(
            Revenue.user_id == current_user.id,
            Revenue.is_active == True,
            Revenue.start_date <= month_start.date()
        ).all()

        revenues_total = sum(
            revenue.amount if revenue.billing_cycle == 'monthly' else
            revenue.amount / 3 if revenue.billing_cycle == 'quarterly' else
            revenue.amount / 12 if revenue.billing_cycle == 'yearly' else 0
            for revenue in revenues
        )

        # Chèques émis pour ce mois
        month_end = (month_start.replace(day=1) + timedelta(days=32)).replace(day=1)
        checks = Check.query.filter(
            Check.user_id == current_user.id,
            Check.check_date >= month_start.date(),
            Check.check_date < month_end.date(),
            Check.status.in_(['pending', 'cashed'])
        ).all()

        checks_total = sum(check.amount for check in checks)

        # Achats CB pour ce mois
        card_purchases = CardPurchase.query.filter(
            CardPurchase.user_id == current_user.id,
            CardPurchase.purchase_date >= month_start,
            CardPurchase.purchase_date < month_end,
            CardPurchase.is_active == True
        ).all()

        card_purchases_total = sum(purchase.amount for purchase in card_purchases)

        # Insérer au début pour avoir l'ordre chronologique
        monthly_subscriptions.insert(0, {
            'month': month_label,
            'total': round(subscriptions_total, 2)
        })
        monthly_credits_data.insert(0, {
            'month': month_label,
            'total': round(credits_total, 2)
        })
        monthly_revenues_data.insert(0, {
            'month': month_label,
            'total': round(revenues_total, 2)
        })
        monthly_expenses_data.insert(0, {
            'month': month_label,
            'total': round(checks_total + card_purchases_total, 2)
        })

    return jsonify({
        'monthly_spending': monthly_subscriptions,
        'monthly_credits': monthly_credits_data,
        'monthly_revenues': monthly_revenues_data,
        'monthly_expenses': monthly_expenses_data,
        'total_subscriptions': current_user.get_active_subscriptions_count(),
        'plan': current_user.plan.name if current_user.plan else 'Free'
    })


@bp.route('/subscriptions/distribution')
@login_required
def subscriptions_distribution():
    """API endpoint pour récupérer la répartition des abonnements actifs"""

    # Récupérer tous les abonnements actifs de l'utilisateur
    active_subscriptions = current_user.subscriptions.filter_by(is_active=True).all()

    # Répartition par service
    services_data = {}
    for sub in active_subscriptions:
        # Calculer le montant mensuel
        if sub.billing_cycle == 'monthly':
            monthly_amount = sub.amount
        elif sub.billing_cycle == 'quarterly':
            monthly_amount = sub.amount / 3
        elif sub.billing_cycle == 'yearly':
            monthly_amount = sub.amount / 12
        elif sub.billing_cycle == 'weekly':
            monthly_amount = sub.amount * 4
        else:
            monthly_amount = sub.amount

        # Grouper par service
        if sub.service:
            service_name = sub.service.name
        else:
            service_name = 'Autre'

        if service_name in services_data:
            services_data[service_name] += monthly_amount
        else:
            services_data[service_name] = monthly_amount

    # Répartition par catégorie avec couleurs
    categories_data = {}
    categories_colors = {}
    for sub in active_subscriptions:
        # Calculer le montant mensuel
        if sub.billing_cycle == 'monthly':
            monthly_amount = sub.amount
        elif sub.billing_cycle == 'quarterly':
            monthly_amount = sub.amount / 3
        elif sub.billing_cycle == 'yearly':
            monthly_amount = sub.amount / 12
        elif sub.billing_cycle == 'weekly':
            monthly_amount = sub.amount * 4
        else:
            monthly_amount = sub.amount

        # Group by category
        if sub.category:
            category_name = sub.category.name
            category_color = sub.category.color if sub.category.color else '#6c757d'
        else:
            category_name = 'Uncategorized'
            category_color = '#6c757d'

        if category_name in categories_data:
            categories_data[category_name] += monthly_amount
        else:
            categories_data[category_name] = monthly_amount
            categories_colors[category_name] = category_color

    # Formater les données pour Chart.js
    services_labels = list(services_data.keys())
    services_values = [round(v, 2) for v in services_data.values()]

    categories_labels = list(categories_data.keys())
    categories_values = [round(v, 2) for v in categories_data.values()]
    categories_colors_list = [categories_colors[label] for label in categories_labels]

    return jsonify({
        'services': {
            'labels': services_labels,
            'values': services_values
        },
        'categories': {
            'labels': categories_labels,
            'values': categories_values,
            'colors': categories_colors_list
        }
    })


@bp.route('/credits/distribution')
@login_required
def credits_distribution():
    """API endpoint pour récupérer la répartition des crédits actifs par type"""

    # Récupérer tous les crédits actifs de l'utilisateur
    active_credits = current_user.credits.filter_by(is_active=True).all()

    # Répartition par type de crédit avec couleurs
    types_data = {}
    types_colors = {}
    for credit in active_credits:
        # Calculer le montant mensuel
        if credit.billing_cycle == 'monthly':
            monthly_amount = credit.amount
        elif credit.billing_cycle == 'quarterly':
            monthly_amount = credit.amount / 3
        elif credit.billing_cycle == 'yearly':
            monthly_amount = credit.amount / 12
        else:
            monthly_amount = credit.amount

        # Group by credit type
        if credit.credit_type_obj:
            type_name = credit.credit_type_obj.name
            type_color = credit.credit_type_obj.color if credit.credit_type_obj.color else '#6c757d'
        else:
            type_name = 'No type'
            type_color = '#6c757d'

        if type_name in types_data:
            types_data[type_name] += monthly_amount
        else:
            types_data[type_name] = monthly_amount
            types_colors[type_name] = type_color

    # Formater les données pour Chart.js
    types_labels = list(types_data.keys())
    types_values = [round(v, 2) for v in types_data.values()]
    types_colors_list = [types_colors[label] for label in types_labels]

    return jsonify({
        'types': {
            'labels': types_labels,
            'values': types_values,
            'colors': types_colors_list
        }
    })


@bp.route('/card-purchases/distribution')
@login_required
def card_purchases_distribution():
    """API endpoint to retrieve active card purchases distribution"""
    from app.models import CardPurchase

    # Get all active card purchases for the user
    active_purchases = current_user.card_purchases.filter_by(is_active=True).all()

    # Distribution by merchant
    merchants_data = {}
    for purchase in active_purchases:
        merchant_name = purchase.merchant_name if purchase.merchant_name else 'Other'

        if merchant_name in merchants_data:
            merchants_data[merchant_name] += purchase.amount
        else:
            merchants_data[merchant_name] = purchase.amount

    # Distribution by category with colors
    categories_data = {}
    categories_colors = {}
    for purchase in active_purchases:
        if purchase.category:
            category_name = purchase.category.name
            category_color = purchase.category.color if purchase.category.color else '#6c757d'
        else:
            category_name = 'Uncategorized'
            category_color = '#6c757d'

        if category_name in categories_data:
            categories_data[category_name] += purchase.amount
        else:
            categories_data[category_name] = purchase.amount
            categories_colors[category_name] = category_color

    # Formater les données pour Chart.js
    merchants_labels = list(merchants_data.keys())
    merchants_values = [round(v, 2) for v in merchants_data.values()]

    categories_labels = list(categories_data.keys())
    categories_values = [round(v, 2) for v in categories_data.values()]
    categories_colors_list = [categories_colors[label] for label in categories_labels]

    return jsonify({
        'merchants': {
            'labels': merchants_labels,
            'values': merchants_values
        },
        'categories': {
            'labels': categories_labels,
            'values': categories_values,
            'colors': categories_colors_list
        }
    })


@bp.route('/revenues/distribution')
@login_required
def revenues_distribution():
    """API endpoint pour récupérer la répartition des revenus actifs par type"""
    from app.models import Revenue
    from app.routes.revenues import get_revenue_types

    # Définition des types de revenus avec couleurs (avec traductions)
    revenue_types_list = get_revenue_types()
    REVENUE_TYPES = {}
    for code, name, icon, color in revenue_types_list:
        REVENUE_TYPES[code] = {'name': name, 'color': color}

    # Récupérer tous les revenus actifs de l'utilisateur
    active_revenues = current_user.revenues.filter_by(is_active=True).all()

    # Répartition par type de revenu avec couleurs
    types_data = {}
    types_colors = {}
    for revenue in active_revenues:
        # Calculer le montant mensuel
        if revenue.billing_cycle == 'monthly':
            monthly_amount = revenue.amount
        elif revenue.billing_cycle == 'quarterly':
            monthly_amount = revenue.amount / 3
        elif revenue.billing_cycle == 'yearly':
            monthly_amount = revenue.amount / 12
        else:
            monthly_amount = revenue.amount

        # Grouper par type de revenu
        type_code = revenue.revenue_type if revenue.revenue_type else 'other'
        type_info = REVENUE_TYPES.get(type_code, REVENUE_TYPES['other'])
        type_name = type_info['name']
        type_color = type_info['color']

        if type_name in types_data:
            types_data[type_name] += monthly_amount
        else:
            types_data[type_name] = monthly_amount
            types_colors[type_name] = type_color

    # Formater les données pour Chart.js
    types_labels = list(types_data.keys())
    types_values = [round(v, 2) for v in types_data.values()]
    types_colors_list = [types_colors[label] for label in types_labels]

    return jsonify({
        'types': {
            'labels': types_labels,
            'values': types_values,
            'colors': types_colors_list
        }
    })
