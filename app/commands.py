"""
Commandes Flask CLI pour les tâches automatisées
"""
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import click
from flask.cli import with_appcontext
from app import db
from app.models import Subscription, Credit, Revenue, Notification, User, InstallmentPayment, Transaction
from app.utils.transactions import generate_future_transactions, create_transaction_from_revenue, create_transaction_from_subscription, create_transaction_from_credit, create_transaction_from_installment, check_and_regenerate_transactions, update_or_create_transaction
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
    updated_installments = 0

    # Dictionnaire pour suivre les modifications par utilisateur
    # Format: {user_id: {'subscriptions': [...], 'credits': [...], 'revenues': [...], 'credits_terminated': [], 'installments': [], 'installments_completed': [...]}}
    user_updates = defaultdict(lambda: {
        'subscriptions': [],
        'credits': [],
        'revenues': [],
        'credits_terminated': [],
        'installments': [],
        'installments_completed': []
    })

    # Mise à jour des abonnements
    subscriptions = Subscription.query.filter_by(is_active=True).all()
    click.echo(f"Traitement de {len(subscriptions)} abonnement(s) actif(s)...")
    for sub in subscriptions:
        if sub.next_billing_date and sub.next_billing_date <= today:
            click.echo(f"  → Abonnement '{sub.name}' (ID: {sub.id}) - Date: {sub.next_billing_date}")
            # Compter le nombre de paiements passés et mettre à jour/créer des transactions
            payments_count = 0
            while sub.next_billing_date <= today:
                # Mettre à jour ou créer une transaction pour ce paiement
                update_or_create_transaction(sub, 'subscription', transaction_date=sub.next_billing_date, status='completed')

                sub.next_billing_date = calculate_next_date(sub.next_billing_date, sub.billing_cycle)
                payments_count += 1

            # Incrémenter le total payé
            sub.total_paid += (sub.amount * payments_count)
            updated_subscriptions += 1
            click.echo(f"    ✓ {payments_count} paiement(s) traité(s), prochaine date: {sub.next_billing_date}")

            # Enregistrer la modification pour cet utilisateur
            user_updates[sub.user_id]['subscriptions'].append({
                'name': sub.name,
                'amount': sub.amount,
                'payments_count': payments_count,
                'next_date': sub.next_billing_date
            })

    # Mise à jour des crédits
    credits = Credit.query.filter_by(is_active=True).all()
    click.echo(f"Traitement de {len(credits)} crédit(s) actif(s)...")
    for credit in credits:
        if credit.next_payment_date and credit.next_payment_date <= today:
            click.echo(f"  → Crédit '{credit.name}' (ID: {credit.id}) - Date: {credit.next_payment_date}")
            # Compter le nombre de paiements passés et mettre à jour/créer des transactions
            payments_count = 0
            while credit.next_payment_date <= today:
                # Mettre à jour ou créer une transaction pour ce paiement
                update_or_create_transaction(credit, 'credit', transaction_date=credit.next_payment_date, status='completed')

                credit.next_payment_date = calculate_next_date(credit.next_payment_date, credit.billing_cycle)
                payments_count += 1

            # Incrémenter le total payé
            credit.total_paid += (credit.amount * payments_count)

            # Vérifier si le crédit est terminé
            is_terminated = False
            if credit.end_date and credit.next_payment_date > credit.end_date:
                credit.is_active = False
                is_terminated = True
                click.echo(f"    ✗ Crédit '{credit.name}' terminé")

            updated_credits += 1
            click.echo(f"    ✓ {payments_count} paiement(s) traité(s), prochaine date: {credit.next_payment_date}")

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
    click.echo(f"Traitement de {len(revenues)} revenu(s) actif(s)...")
    for revenue in revenues:
        if revenue.next_payment_date and revenue.next_payment_date <= today:
            click.echo(f"  → Revenu '{revenue.name}' (ID: {revenue.id}) - Date: {revenue.next_payment_date}")
            # Compter le nombre de versements passés et mettre à jour/créer des transactions
            payments_count = 0
            while revenue.next_payment_date <= today:
                # Mettre à jour ou créer une transaction pour ce versement
                update_or_create_transaction(revenue, 'revenue', transaction_date=revenue.next_payment_date, status='completed')

                revenue.next_payment_date = calculate_next_date(revenue.next_payment_date, revenue.billing_cycle)
                payments_count += 1

            # Incrémenter le total reçu
            revenue.total_paid += (revenue.amount * payments_count)
            updated_revenues += 1
            click.echo(f"    ✓ {payments_count} versement(s) traité(s), prochaine date: {revenue.next_payment_date}")

            # Enregistrer la modification pour cet utilisateur
            user_updates[revenue.user_id]['revenues'].append({
                'name': revenue.name,
                'amount': revenue.amount,
                'payments_count': payments_count,
                'next_date': revenue.next_payment_date
            })

    # Mise à jour des paiements en plusieurs fois
    installments = InstallmentPayment.query.filter_by(is_active=True).all()
    click.echo(f"Traitement de {len(installments)} paiement(s) en plusieurs fois actif(s)...")
    for installment in installments:
        if installment.next_payment_date and installment.next_payment_date <= today:
            click.echo(f"  → Paiement '{installment.name}' (ID: {installment.id}) - Date: {installment.next_payment_date}")
            # Traiter les paiements en retard et mettre à jour/créer des transactions
            while installment.next_payment_date <= today and installment.installments_paid < installment.number_of_installments:
                # Mettre à jour ou créer une transaction pour ce paiement
                update_or_create_transaction(installment, 'installment', transaction_date=installment.next_payment_date, status='completed')

                installment.installments_paid += 1
                installment.next_payment_date = installment.calculate_next_payment_date()
                updated_installments += 1

                # Vérifier si le paiement est terminé
                if installment.installments_paid >= installment.number_of_installments:
                    installment.is_completed = True
                    installment.is_active = False
                    installment.completed_at = datetime.utcnow()

                    # Ajouter aux paiements terminés
                    user_updates[installment.user_id]['installments_completed'].append({
                        'name': installment.name,
                        'total_amount': installment.total_amount
                    })
                    click.echo(f"    ✗ Paiement en plusieurs fois '{installment.name}' terminé")
                    break
                else:
                    # Ajouter aux paiements traités
                    user_updates[installment.user_id]['installments'].append({
                        'name': installment.name,
                        'amount': installment.installment_amount,
                        'installments_paid': installment.installments_paid,
                        'number_of_installments': installment.number_of_installments,
                        'next_date': installment.next_payment_date
                    })
            click.echo(f"    ✓ Paiement traité, {installment.installments_paid}/{installment.number_of_installments} échéances")

    # Vérifier et régénérer les transactions futures si nécessaire (< 3 mois restants)
    click.echo("Vérification et régénération des transactions futures...")
    regenerated_count = 0

    # Vérifier tous les revenus actifs
    for revenue in Revenue.query.filter_by(is_active=True).all():
        if check_and_regenerate_transactions(revenue, 'revenue', min_months=3, generate_months=12):
            regenerated_count += 1

    # Vérifier tous les abonnements actifs
    for subscription in Subscription.query.filter_by(is_active=True).all():
        if check_and_regenerate_transactions(subscription, 'subscription', min_months=3, generate_months=12):
            regenerated_count += 1

    # Vérifier tous les crédits actifs
    for credit in Credit.query.filter_by(is_active=True).all():
        if check_and_regenerate_transactions(credit, 'credit', min_months=3, generate_months=12):
            regenerated_count += 1

    # Vérifier tous les paiements en plusieurs fois actifs
    for installment in InstallmentPayment.query.filter_by(is_active=True).all():
        # Pour les installments, on ne génère que les mensualités restantes
        remaining = installment.number_of_installments - installment.installments_paid
        if remaining > 0 and check_and_regenerate_transactions(installment, 'installment', min_months=1, generate_months=remaining):
            regenerated_count += 1

    if regenerated_count > 0:
        click.echo(f"✓ {regenerated_count} entité(s) ont eu leurs transactions régénérées")

    # Sauvegarder les modifications
    db.session.commit()

    # Créer des notifications et envoyer des emails pour chaque utilisateur concerné
    notifications_created = 0
    for user_id, updates in user_updates.items():
        user = User.query.get(user_id)
        if not user:
            continue

        # Construire le message récapitulatif
        message_sections = []

        if updates['subscriptions']:
            section = f"📅 {len(updates['subscriptions'])} abonnement(s) mis à jour\n"
            for sub in updates['subscriptions']:
                section += f"  • {sub['name']}: {sub['payments_count']} paiement(s) de {sub['amount']:.2f}€\n"
            message_sections.append(section.rstrip())

        if updates['revenues']:
            section = f"💰 {len(updates['revenues'])} revenu(s) mis à jour\n"
            for revenue in updates['revenues']:
                section += f"  • {revenue['name']}: {revenue['payments_count']} versement(s) de {revenue['amount']:.2f}€\n"
            message_sections.append(section.rstrip())

        if updates['credits']:
            section = f"💳 {len(updates['credits'])} crédit(s) mis à jour\n"
            for credit in updates['credits']:
                section += f"  • {credit['name']}: {credit['payments_count']} paiement(s) de {credit['amount']:.2f}€\n"
            message_sections.append(section.rstrip())

        if updates['credits_terminated']:
            section = f"✅ {len(updates['credits_terminated'])} crédit(s) terminé(s)\n"
            for credit in updates['credits_terminated']:
                section += f"  • {credit['name']}\n"
            message_sections.append(section.rstrip())

        if updates['installments']:
            total_installments = len(updates['installments'])
            section = f"📆 {total_installments} paiement(s) en plusieurs fois traité(s)\n"
            for installment in updates['installments']:
                section += f"  • {installment['name']}: {installment['installments_paid']}/{installment['number_of_installments']} - {installment['amount']:.2f}€\n"
            message_sections.append(section.rstrip())

        if updates['installments_completed']:
            section = f"🎉 {len(updates['installments_completed'])} paiement(s) en plusieurs fois terminé(s)\n"
            for installment in updates['installments_completed']:
                section += f"  • {installment['name']}\n"
            message_sections.append(section.rstrip())

        if message_sections:
            message = "\n\n".join(message_sections)
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
        from flask import current_app

        # Créer un contexte de requête pour permettre l'utilisation de url_for()
        with current_app.test_request_context():
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
    click.echo(f"  - Paiements en plusieurs fois: {updated_installments}")
    click.echo(f"  - Notifications créées: {notifications_created}")


@click.command('archive-old-notifications')
@with_appcontext
def archive_old_notifications():
    """Archive automatiquement les notifications lues de plus de 30 jours"""
    threshold_date = datetime.now() - timedelta(days=30)

    # Trouver toutes les notifications lues depuis plus de 30 jours et non archivées
    notifications_to_archive = Notification.query.filter(
        Notification.is_read == True,
        Notification.archived == False,
        Notification.read_at <= threshold_date
    ).all()

    archived_count = 0
    for notification in notifications_to_archive:
        notification.archived = True
        notification.archived_at = datetime.utcnow()
        archived_count += 1

    db.session.commit()

    click.echo(f"✓ {archived_count} notification(s) archivée(s)")


@click.command('generate-initial-transactions')
@click.option('--months', default=12, help='Nombre de mois de transactions à générer')
@with_appcontext
def generate_initial_transactions(months):
    """Génère les transactions initiales pour toutes les entités actives"""
    click.echo(f"Génération des transactions pour les {months} prochains mois...")

    total_transactions = 0

    # Générer les transactions pour les revenus
    revenues = Revenue.query.filter_by(is_active=True).all()
    for revenue in revenues:
        transactions = generate_future_transactions(revenue, 'revenue', months_ahead=months)
        total_transactions += len(transactions)
    click.echo(f"  - Revenus: {len(revenues)} revenus traités")

    # Générer les transactions pour les abonnements
    subscriptions = Subscription.query.filter_by(is_active=True).all()
    for subscription in subscriptions:
        transactions = generate_future_transactions(subscription, 'subscription', months_ahead=months)
        total_transactions += len(transactions)
    click.echo(f"  - Abonnements: {len(subscriptions)} abonnements traités")

    # Générer les transactions pour les crédits
    credits = Credit.query.filter_by(is_active=True).all()
    for credit in credits:
        transactions = generate_future_transactions(credit, 'credit', months_ahead=months)
        total_transactions += len(transactions)
    click.echo(f"  - Crédits: {len(credits)} crédits traités")

    # Générer les transactions pour les paiements en plusieurs fois
    installments = InstallmentPayment.query.filter_by(is_active=True).all()
    for installment in installments:
        transactions = generate_future_transactions(installment, 'installment', months_ahead=months)
        total_transactions += len(transactions)
    click.echo(f"  - Paiements en plusieurs fois: {len(installments)} paiements traités")

    db.session.commit()
    click.echo(f"✓ {total_transactions} transactions générées avec succès")


def init_app(app):
    """Enregistre les commandes dans l'application Flask"""
    app.cli.add_command(update_payment_dates)
    app.cli.add_command(archive_old_notifications)
    app.cli.add_command(generate_initial_transactions)
