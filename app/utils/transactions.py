"""
Fonctions utilitaires pour la gestion des transactions financières
"""
from datetime import datetime
from dateutil.relativedelta import relativedelta
from app import db
from app.models import Transaction, Revenue, Subscription, Credit, InstallmentPayment


def create_transaction_from_revenue(revenue, transaction_date=None, status='pending'):
    """
    Crée une transaction à partir d'un revenu

    Args:
        revenue: Objet Revenue
        transaction_date: Date de la transaction (défaut: next_payment_date)
        status: Statut de la transaction ('pending', 'completed', 'cancelled')

    Returns:
        Transaction créée
    """
    if transaction_date is None:
        transaction_date = revenue.next_payment_date

    # Récupérer le nom de la catégorie (employeur)
    category_name = revenue.employer.name if revenue.employer else 'Autres revenus'

    transaction = Transaction(
        user_id=revenue.user_id,
        transaction_date=transaction_date,
        transaction_type='revenue',
        source_id=revenue.id,
        source_type='revenue',
        name=revenue.name,
        description=revenue.description,
        amount=revenue.amount,
        currency=revenue.currency,
        is_positive=True,
        category_name=category_name,
        status=status
    )

    db.session.add(transaction)
    return transaction


def create_transaction_from_subscription(subscription, transaction_date=None, status='pending'):
    """
    Crée une transaction à partir d'un abonnement

    Args:
        subscription: Objet Subscription
        transaction_date: Date de la transaction (défaut: next_billing_date)
        status: Statut de la transaction ('pending', 'completed', 'cancelled')

    Returns:
        Transaction créée
    """
    if transaction_date is None:
        transaction_date = subscription.next_billing_date

    # Récupérer le nom de la catégorie
    category_name = subscription.category.name if subscription.category else 'Non catégorisé'

    transaction = Transaction(
        user_id=subscription.user_id,
        transaction_date=transaction_date,
        transaction_type='subscription',
        source_id=subscription.id,
        source_type='subscription',
        name=subscription.name,
        description=subscription.description,
        amount=subscription.amount,
        currency=subscription.currency,
        is_positive=False,
        category_name=category_name,
        status=status
    )

    db.session.add(transaction)
    return transaction


def create_transaction_from_credit(credit, transaction_date=None, status='pending'):
    """
    Crée une transaction à partir d'un crédit

    Args:
        credit: Objet Credit
        transaction_date: Date de la transaction (défaut: next_payment_date)
        status: Statut de la transaction ('pending', 'completed', 'cancelled')

    Returns:
        Transaction créée
    """
    if transaction_date is None:
        transaction_date = credit.next_payment_date

    # Récupérer le nom de la catégorie
    category_name = credit.category.name if credit.category else 'Crédit'

    transaction = Transaction(
        user_id=credit.user_id,
        transaction_date=transaction_date,
        transaction_type='credit',
        source_id=credit.id,
        source_type='credit',
        name=credit.name,
        description=credit.description,
        amount=credit.amount,
        currency=credit.currency,
        is_positive=False,
        category_name=category_name,
        status=status
    )

    db.session.add(transaction)
    return transaction


def create_transaction_from_installment(installment, transaction_date=None, status='pending'):
    """
    Crée une transaction à partir d'un paiement en plusieurs fois

    Args:
        installment: Objet InstallmentPayment
        transaction_date: Date de la transaction (défaut: next_payment_date)
        status: Statut de la transaction ('pending', 'completed', 'cancelled')

    Returns:
        Transaction créée
    """
    if transaction_date is None:
        transaction_date = installment.next_payment_date

    # Récupérer le nom de la catégorie
    category_name = installment.product_category or 'Paiement en plusieurs fois'

    transaction = Transaction(
        user_id=installment.user_id,
        transaction_date=transaction_date,
        transaction_type='installment',
        source_id=installment.id,
        source_type='installment',
        name=installment.name,
        description=installment.description,
        amount=installment.installment_amount,
        currency=installment.currency,
        is_positive=False,
        category_name=category_name,
        status=status
    )

    db.session.add(transaction)
    return transaction


def generate_future_transactions(source_object, source_type, months_ahead=12):
    """
    Génère des transactions futures pour un objet source

    Args:
        source_object: Objet Revenue, Subscription, Credit ou InstallmentPayment
        source_type: Type de l'objet ('revenue', 'subscription', 'credit', 'installment')
        months_ahead: Nombre de mois à générer (défaut: 12)

    Returns:
        Liste des transactions créées
    """
    transactions = []

    # Fonction de création selon le type
    create_func = {
        'revenue': create_transaction_from_revenue,
        'subscription': create_transaction_from_subscription,
        'credit': create_transaction_from_credit,
        'installment': create_transaction_from_installment
    }.get(source_type)

    if not create_func:
        return transactions

    # Déterminer la date de début et le cycle
    if source_type == 'revenue':
        current_date = source_object.next_payment_date
        billing_cycle = source_object.billing_cycle
    elif source_type == 'subscription':
        current_date = source_object.next_billing_date
        billing_cycle = source_object.billing_cycle
    elif source_type == 'credit':
        current_date = source_object.next_payment_date
        billing_cycle = source_object.billing_cycle
    elif source_type == 'installment':
        current_date = source_object.next_payment_date
        # Les paiements en plusieurs fois sont toujours mensuels
        remaining_installments = source_object.number_of_installments - source_object.installments_paid
        months_ahead = min(months_ahead, remaining_installments)
        billing_cycle = 'monthly'

    # Générer les transactions futures
    end_date = datetime.now().date() + relativedelta(months=months_ahead)

    while current_date <= end_date:
        # Créer la transaction
        transaction = create_func(source_object, transaction_date=current_date, status='pending')
        transactions.append(transaction)

        # Calculer la prochaine date selon le cycle
        if billing_cycle == 'monthly':
            current_date = current_date + relativedelta(months=1)
        elif billing_cycle == 'quarterly':
            current_date = current_date + relativedelta(months=3)
        elif billing_cycle == 'yearly':
            current_date = current_date + relativedelta(years=1)
        elif billing_cycle == 'weekly':
            current_date = current_date + relativedelta(weeks=1)
        else:
            break  # Cycle non reconnu

        # Pour les paiements en plusieurs fois, arrêter quand toutes les mensualités sont créées
        if source_type == 'installment':
            if len(transactions) >= remaining_installments:
                break

    return transactions


def cancel_future_transactions(source_id, source_type):
    """
    Annule toutes les transactions futures pour un objet source

    Args:
        source_id: ID de l'objet source
        source_type: Type de l'objet ('revenue', 'subscription', 'credit', 'installment')
    """
    today = datetime.now().date()

    # Récupérer toutes les transactions futures
    future_transactions = Transaction.query.filter(
        Transaction.source_id == source_id,
        Transaction.source_type == source_type,
        Transaction.transaction_date > today,
        Transaction.status == 'pending'
    ).all()

    # Marquer comme annulées
    for transaction in future_transactions:
        transaction.status = 'cancelled'

    db.session.commit()


def update_future_transactions(source_object, source_type):
    """
    Met à jour les transactions futures après modification de l'objet source

    Args:
        source_object: Objet Revenue, Subscription, Credit ou InstallmentPayment modifié
        source_type: Type de l'objet ('revenue', 'subscription', 'credit', 'installment')
    """
    today = datetime.now().date()

    # Annuler les anciennes transactions futures
    cancel_future_transactions(source_object.id, source_type)

    # Régénérer les nouvelles transactions futures
    generate_future_transactions(source_object, source_type)

    db.session.commit()


def check_and_regenerate_transactions(source_object, source_type, min_months=3, generate_months=12):
    """
    Vérifie s'il reste suffisamment de transactions futures et en génère si nécessaire

    Args:
        source_object: Objet Revenue, Subscription, Credit ou InstallmentPayment
        source_type: Type de l'objet ('revenue', 'subscription', 'credit', 'installment')
        min_months: Nombre minimum de mois de transactions futures requis (défaut: 3)
        generate_months: Nombre de mois à générer si insuffisant (défaut: 12)
    """
    from dateutil.relativedelta import relativedelta

    today = datetime.now().date()
    threshold_date = today + relativedelta(months=min_months)

    # Compter les transactions futures (pending) au-delà du seuil
    future_transactions_count = Transaction.query.filter(
        Transaction.source_id == source_object.id,
        Transaction.source_type == source_type,
        Transaction.status == 'pending',
        Transaction.transaction_date > threshold_date
    ).count()

    # Si moins de transactions que le seuil, en générer de nouvelles
    if future_transactions_count < min_months:
        # Trouver la date de la dernière transaction future
        last_transaction = Transaction.query.filter(
            Transaction.source_id == source_object.id,
            Transaction.source_type == source_type,
            Transaction.status == 'pending'
        ).order_by(Transaction.transaction_date.desc()).first()

        if last_transaction:
            # Générer à partir de la prochaine date après la dernière transaction
            start_date = last_transaction.transaction_date
        else:
            # Aucune transaction future, générer à partir de la prochaine date de paiement
            if source_type == 'revenue':
                start_date = source_object.next_payment_date
            elif source_type == 'subscription':
                start_date = source_object.next_billing_date
            elif source_type == 'credit':
                start_date = source_object.next_payment_date
            elif source_type == 'installment':
                start_date = source_object.next_payment_date

        # Générer les transactions supplémentaires
        generate_future_transactions(source_object, source_type, months_ahead=generate_months)
        return True

    return False
