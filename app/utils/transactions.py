"""
Fonctions utilitaires pour la gestion des transactions financières
"""
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from app import db
from app.models import Transaction, Revenue, Subscription, Credit, InstallmentPayment


def calculate_next_future_date(start_date, billing_cycle):
    """
    Calcule la prochaine date de renouvellement future à partir d'une date de début.
    Si la date de début est dans le passé, calcule la prochaine occurrence future.

    Args:
        start_date: Date de début (peut être dans le passé)
        billing_cycle: Cycle de facturation ('weekly', 'monthly', 'quarterly', 'yearly')

    Returns:
        La prochaine date de renouvellement future (> aujourd'hui)
    """
    today = datetime.now().date()
    next_date = start_date

    # Si la date de début est déjà dans le futur, on calcule juste le premier renouvellement
    if start_date > today:
        if billing_cycle == 'weekly':
            return start_date + timedelta(weeks=1)
        elif billing_cycle == 'monthly':
            return start_date + relativedelta(months=1)
        elif billing_cycle == 'quarterly':
            return start_date + relativedelta(months=3)
        elif billing_cycle == 'yearly':
            return start_date + relativedelta(years=1)
        return start_date

    # Sinon, on calcule la prochaine occurrence future
    while next_date <= today:
        if billing_cycle == 'weekly':
            next_date = next_date + timedelta(weeks=1)
        elif billing_cycle == 'monthly':
            next_date = next_date + relativedelta(months=1)
        elif billing_cycle == 'quarterly':
            next_date = next_date + relativedelta(months=3)
        elif billing_cycle == 'yearly':
            next_date = next_date + relativedelta(years=1)
        else:
            # Si le cycle n'est pas reconnu, retourner la date de début
            return start_date

    return next_date


def update_or_create_transaction(source_object, source_type, transaction_date, status='completed'):
    """
    Met à jour une transaction existante ou en crée une nouvelle si elle n'existe pas

    Args:
        source_object: Objet Revenue, Subscription, Credit ou InstallmentPayment
        source_type: Type de l'objet ('revenue', 'subscription', 'credit', 'installment')
        transaction_date: Date de la transaction
        status: Statut de la transaction ('pending', 'completed', 'cancelled')

    Returns:
        Transaction créée ou mise à jour
    """
    # Chercher une transaction existante pour cette date et cette source
    existing_transaction = Transaction.query.filter_by(
        source_id=source_object.id,
        source_type=source_type,
        transaction_date=transaction_date
    ).first()

    if existing_transaction:
        # Mettre à jour le statut de la transaction existante
        old_status = existing_transaction.status
        existing_transaction.status = status

        # Forcer SQLAlchemy à détecter le changement
        db.session.add(existing_transaction)
        db.session.flush()

        # Log si le statut a changé
        if old_status != status:
            print(f"✓ Transaction mise à jour: {source_type} #{source_object.id} du {transaction_date} - {old_status} → {status}")

        return existing_transaction
    else:
        # Créer une nouvelle transaction si elle n'existe pas
        create_func = {
            'revenue': create_transaction_from_revenue,
            'subscription': create_transaction_from_subscription,
            'credit': create_transaction_from_credit,
            'installment': create_transaction_from_installment
        }.get(source_type)

        if create_func:
            transaction = create_func(source_object, transaction_date=transaction_date, status=status)
            print(f"✓ Transaction créée: {source_type} #{source_object.id} du {transaction_date} - statut: {status}")
            return transaction
        return None


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


def generate_future_transactions(source_object, source_type, months_ahead=12, include_past=True):
    """
    Génère des transactions pour un objet source (passées et futures)

    Args:
        source_object: Objet Revenue, Subscription, Credit ou InstallmentPayment
        source_type: Type de l'objet ('revenue', 'subscription', 'credit', 'installment')
        months_ahead: Nombre de mois futurs à générer (défaut: 12)
        include_past: Générer aussi les transactions passées depuis start_date (défaut: True)

    Returns:
        Liste des transactions créées
    """
    transactions = []
    today = datetime.now().date()

    # Fonction de création selon le type
    create_func = {
        'revenue': create_transaction_from_revenue,
        'subscription': create_transaction_from_subscription,
        'credit': create_transaction_from_credit,
        'installment': create_transaction_from_installment
    }.get(source_type)

    if not create_func:
        return transactions

    # Déterminer la date de début, le cycle et la start_date
    if source_type == 'revenue':
        start_date = source_object.start_date
        billing_cycle = source_object.billing_cycle
    elif source_type == 'subscription':
        start_date = source_object.start_date
        billing_cycle = source_object.billing_cycle
    elif source_type == 'credit':
        start_date = source_object.start_date
        billing_cycle = source_object.billing_cycle
    elif source_type == 'installment':
        start_date = source_object.start_date
        billing_cycle = 'monthly'  # Toujours mensuel
        remaining_installments = source_object.number_of_installments - source_object.installments_paid

    # Commencer par la start_date si on inclut le passé, sinon par next_payment_date
    if include_past:
        current_date = start_date
    else:
        if source_type == 'revenue':
            current_date = source_object.next_payment_date
        elif source_type == 'subscription':
            current_date = source_object.next_billing_date
        elif source_type == 'credit':
            current_date = source_object.next_payment_date
        elif source_type == 'installment':
            current_date = source_object.next_payment_date

    # Date de fin : aujourd'hui + months_ahead
    end_date = today + relativedelta(months=months_ahead)

    # Générer les transactions
    transaction_count = 0
    while current_date <= end_date:
        # Déterminer le statut : 'completed' pour les transactions passées, 'pending' pour les futures
        transaction_status = 'completed' if current_date < today else 'pending'

        # Vérifier si une transaction existe déjà pour cette date
        existing_transaction = Transaction.query.filter_by(
            source_id=source_object.id,
            source_type=source_type,
            transaction_date=current_date
        ).first()

        if existing_transaction:
            # Si la transaction existe déjà, mettre à jour ses champs
            # IMPORTANT: Ne mettre à jour que les transactions futures (>= aujourd'hui)
            # Les transactions passées ne doivent pas être modifiées
            if current_date >= today:
                # Mise à jour complète pour les transactions futures
                existing_transaction.status = transaction_status
                existing_transaction.name = source_object.name
                existing_transaction.description = source_object.description
                existing_transaction.currency = source_object.currency

                # Mettre à jour le montant selon le type de source
                if source_type == 'installment':
                    existing_transaction.amount = source_object.installment_amount
                else:
                    existing_transaction.amount = source_object.amount

                # Mettre à jour la catégorie selon le type de source
                if source_type == 'revenue':
                    existing_transaction.category_name = source_object.employer.name if source_object.employer else 'Autres revenus'
                elif source_type == 'subscription':
                    existing_transaction.category_name = source_object.category.name if source_object.category else 'Non catégorisé'
                elif source_type == 'credit':
                    existing_transaction.category_name = source_object.category.name if source_object.category else 'Crédit'
                elif source_type == 'installment':
                    existing_transaction.category_name = source_object.product_category or 'Paiement en plusieurs fois'

                db.session.add(existing_transaction)
                db.session.flush()
            else:
                # Pour les transactions passées, mettre à jour uniquement le statut si nécessaire
                if existing_transaction.status != transaction_status:
                    existing_transaction.status = transaction_status
                    db.session.add(existing_transaction)
                    db.session.flush()

            transactions.append(existing_transaction)
        else:
            # Créer une nouvelle transaction
            transaction = create_func(source_object, transaction_date=current_date, status=transaction_status)
            transactions.append(transaction)

        transaction_count += 1

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
            if transaction_count >= source_object.number_of_installments:
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


def delete_all_transactions(source_id, source_type):
    """
    Supprime toutes les transactions (passées et futures) pour un objet source

    Args:
        source_id: ID de l'objet source
        source_type: Type de l'objet ('revenue', 'subscription', 'credit', 'installment')
    """
    # Récupérer toutes les transactions liées à cet objet
    transactions = Transaction.query.filter(
        Transaction.source_id == source_id,
        Transaction.source_type == source_type
    ).all()

    # Supprimer toutes les transactions
    for transaction in transactions:
        db.session.delete(transaction)

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
