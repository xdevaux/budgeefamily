"""
Commandes Flask CLI pour les tâches automatisées
"""
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import click
from flask.cli import with_appcontext
from app import db
from app.models import Subscription, Credit, Revenue, Notification, User
from collections import defaultdict


def calculate_next_date(current_date, billing_cycle):
    """Calcule la prochaine date en fonction du cycle de facturation"""
    if billing_cycle == 'monthly':
        return current_date + relativedelta(months=1)
    elif billing_cycle == 'quarterly':
        return current_date + relativedelta(months=3)
    elif billing_cycle == 'yearly':
        return current_date + relativedelta(years=1)
    elif billing_cycle == 'weekly':
        return current_date + timedelta(weeks=1)
    else:
        return current_date


@click.command('update-payment-dates')
@with_appcontext
def update_payment_dates():
    """Met à jour les dates de prochains paiements/versements pour tous les éléments actifs"""
    today = datetime.now().date()

    updated_subscriptions = 0
    updated_credits = 0
    updated_revenues = 0

    # Dictionnaire pour suivre les modifications par utilisateur
    # Format: {user_id: {'subscriptions': [...], 'credits': [...], 'revenues': [...], 'credits_terminated': [...]}}
    user_updates = defaultdict(lambda: {
        'subscriptions': [],
        'credits': [],
        'revenues': [],
        'credits_terminated': []
    })

    # Mise à jour des abonnements
    subscriptions = Subscription.query.filter_by(is_active=True).all()
    for sub in subscriptions:
        if sub.next_billing_date and sub.next_billing_date <= today:
            # Compter le nombre de paiements passés
            payments_count = 0
            while sub.next_billing_date <= today:
                sub.next_billing_date = calculate_next_date(sub.next_billing_date, sub.billing_cycle)
                payments_count += 1

            # Incrémenter le total payé
            sub.total_paid += (sub.amount * payments_count)
            updated_subscriptions += 1

            # Enregistrer la modification pour cet utilisateur
            user_updates[sub.user_id]['subscriptions'].append({
                'name': sub.name,
                'amount': sub.amount,
                'payments_count': payments_count,
                'next_date': sub.next_billing_date
            })

    # Mise à jour des crédits
    credits = Credit.query.filter_by(is_active=True).all()
    for credit in credits:
        if credit.next_payment_date and credit.next_payment_date <= today:
            # Compter le nombre de paiements passés
            payments_count = 0
            while credit.next_payment_date <= today:
                credit.next_payment_date = calculate_next_date(credit.next_payment_date, credit.billing_cycle)
                payments_count += 1

            # Incrémenter le total payé
            credit.total_paid += (credit.amount * payments_count)

            # Vérifier si le crédit est terminé
            is_terminated = False
            if credit.end_date and credit.next_payment_date > credit.end_date:
                credit.is_active = False
                is_terminated = True
                click.echo(f"Crédit '{credit.name}' terminé")

            updated_credits += 1

            # Enregistrer la modification pour cet utilisateur
            if is_terminated:
                user_updates[credit.user_id]['credits_terminated'].append({
                    'name': credit.name
                })
            else:
                user_updates[credit.user_id]['credits'].append({
                    'name': credit.name,
                    'amount': credit.amount,
                    'payments_count': payments_count,
                    'next_date': credit.next_payment_date
                })

    # Mise à jour des revenus
    revenues = Revenue.query.filter_by(is_active=True).all()
    for revenue in revenues:
        if revenue.next_payment_date and revenue.next_payment_date <= today:
            # Compter le nombre de versements passés
            payments_count = 0
            while revenue.next_payment_date <= today:
                revenue.next_payment_date = calculate_next_date(revenue.next_payment_date, revenue.billing_cycle)
                payments_count += 1

            # Incrémenter le total reçu
            revenue.total_paid += (revenue.amount * payments_count)
            updated_revenues += 1

            # Enregistrer la modification pour cet utilisateur
            user_updates[revenue.user_id]['revenues'].append({
                'name': revenue.name,
                'amount': revenue.amount,
                'payments_count': payments_count,
                'next_date': revenue.next_payment_date
            })

    # Sauvegarder les modifications
    db.session.commit()

    # Créer des notifications et envoyer des emails pour chaque utilisateur concerné
    notifications_created = 0
    for user_id, updates in user_updates.items():
        user = User.query.get(user_id)
        if not user:
            continue

        # Construire le message récapitulatif
        message_parts = []

        if updates['subscriptions']:
            message_parts.append(f"📅 {len(updates['subscriptions'])} abonnement(s) mis à jour")
            for sub in updates['subscriptions']:
                message_parts.append(f"  • {sub['name']}: {sub['payments_count']} paiement(s) de {sub['amount']:.2f}€")

        if updates['credits']:
            message_parts.append(f"💳 {len(updates['credits'])} crédit(s) mis à jour")
            for credit in updates['credits']:
                message_parts.append(f"  • {credit['name']}: {credit['payments_count']} paiement(s) de {credit['amount']:.2f}€")

        if updates['credits_terminated']:
            message_parts.append(f"✅ {len(updates['credits_terminated'])} crédit(s) terminé(s)")
            for credit in updates['credits_terminated']:
                message_parts.append(f"  • {credit['name']}")

        if updates['revenues']:
            message_parts.append(f"💰 {len(updates['revenues'])} revenu(s) mis à jour")
            for revenue in updates['revenues']:
                message_parts.append(f"  • {revenue['name']}: {revenue['payments_count']} versement(s) de {revenue['amount']:.2f}€")

        if message_parts:
            message = "\n".join(message_parts)
            message += "\n\n⚙️ Traitement automatisé par Budgee Family"

            # Créer la notification
            notification = Notification(
                user_id=user_id,
                type='daily_update',
                title='Mise à jour automatique quotidienne',
                message=message
            )
            db.session.add(notification)
            notifications_created += 1

    db.session.commit()

    # Envoyer les emails de notification
    if notifications_created > 0:
        from app.utils.email import send_notification_email
        for user_id in user_updates.keys():
            user = User.query.get(user_id)
            if user:
                # Récupérer la dernière notification créée pour cet utilisateur
                notification = Notification.query.filter_by(
                    user_id=user_id,
                    type='daily_update'
                ).order_by(Notification.created_at.desc()).first()

                if notification:
                    send_notification_email(user, notification)

    click.echo(f"✓ Dates mises à jour avec succès:")
    click.echo(f"  - Abonnements: {updated_subscriptions}")
    click.echo(f"  - Crédits: {updated_credits}")
    click.echo(f"  - Revenus: {updated_revenues}")
    click.echo(f"  - Notifications créées: {notifications_created}")


def init_app(app):
    """Enregistre les commandes dans l'application Flask"""
    app.cli.add_command(update_payment_dates)
