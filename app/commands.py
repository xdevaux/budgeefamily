"""
Commandes Flask CLI pour les tâches automatisées
"""
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import click
from flask.cli import with_appcontext
from app import db
from app.models import Subscription, Credit, Revenue


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
            if credit.end_date and credit.next_payment_date > credit.end_date:
                credit.is_active = False
                click.echo(f"Crédit '{credit.name}' terminé")

            updated_credits += 1

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

    # Sauvegarder les modifications
    db.session.commit()

    click.echo(f"✓ Dates mises à jour avec succès:")
    click.echo(f"  - Abonnements: {updated_subscriptions}")
    click.echo(f"  - Crédits: {updated_credits}")
    click.echo(f"  - Revenus: {updated_revenues}")


def init_app(app):
    """Enregistre les commandes dans l'application Flask"""
    app.cli.add_command(update_payment_dates)
