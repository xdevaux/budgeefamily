from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, session, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Subscription, Category, Plan, Notification, Credit, Revenue, InstallmentPayment, Transaction, Reminder
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

    # Prochains paiements pour les paiements en plusieurs fois - tous les paiements actifs triés par date
    upcoming_installments = current_user.installment_payments.filter(
        InstallmentPayment.is_active == True
    ).order_by(InstallmentPayment.next_payment_date).all()

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

    # Ajouter les paiements en plusieurs fois au total des crédits
    total_installments = sum(
        installment.installment_amount
        for installment in upcoming_installments
    )

    total_credits += total_installments

    # Répartition des revenus par employeur
    revenue_data = {}
    colors_palette = ['#10b981', '#34d399', '#6ee7b7', '#a7f3d0', '#d1fae5', '#ecfdf5']

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

    # Chèques non débités (non pointés dans la balance)
    unpointed_checks = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == 'check',
        Transaction.status == 'completed',
        Transaction.is_pointed == False
    ).order_by(Transaction.transaction_date.desc()).all()

    # Rappels à venir
    from sqlalchemy import or_, and_
    from datetime import date
    today = date.today()
    upcoming_reminders = current_user.reminders.filter(
        Reminder.is_active == True,
        or_(
            Reminder.reminder_year > today.year,
            and_(
                Reminder.reminder_year == today.year,
                Reminder.reminder_month >= today.month
            )
        )
    ).order_by(Reminder.reminder_year, Reminder.reminder_month).limit(10).all()

    return render_template('dashboard.html',
                         active_subscriptions=active_subscriptions,
                         total_subscriptions_cost=round(total_subscriptions_cost, 2),
                         total_monthly_cost=round(total_monthly_cost, 2),
                         upcoming_renewals=upcoming_renewals,
                         upcoming_credits=upcoming_credits,
                         upcoming_revenues=upcoming_revenues,
                         upcoming_installments=upcoming_installments,
                         unpointed_checks=unpointed_checks,
                         upcoming_reminders=upcoming_reminders,
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


@bp.route('/balance')
@login_required
def balance():
    """Page d'affichage du solde avec tous les mouvements (depuis la table transactions)"""
    from calendar import monthrange

    # Récupérer les paramètres de filtre (mois, année et statut)
    now = datetime.utcnow()
    selected_month = request.args.get('month', type=int, default=now.month)
    selected_year = request.args.get('year', type=int, default=now.year)
    selected_status = request.args.get('status', default='all')

    # Calculer le premier et dernier jour du mois sélectionné
    first_day = datetime(selected_year, selected_month, 1).date()
    last_day_num = monthrange(selected_year, selected_month)[1]
    last_day = datetime(selected_year, selected_month, last_day_num).date()

    # Construire la requête de base (transactions du mois, sauf les annulées)
    query = current_user.transactions.filter(
        Transaction.transaction_date >= first_day,
        Transaction.transaction_date <= last_day,
        Transaction.status != 'cancelled'
    )

    # Ajouter le filtre de statut si nécessaire
    if selected_status != 'all':
        query = query.filter(Transaction.status == selected_status)

    # Récupérer les transactions
    transactions = query.order_by(Transaction.transaction_date.desc()).all()

    # Convertir les transactions en dictionnaire pour le template
    movements = []
    for transaction in transactions:
        movement = {
            'id': transaction.id,
            'type': transaction.transaction_type,
            'source_id': transaction.source_id,
            'source_type': transaction.source_type,
            'date': transaction.transaction_date,
            'name': transaction.name,
            'description': transaction.description or '',
            'amount': transaction.amount,
            'currency': transaction.currency,
            'is_positive': transaction.is_positive,
            'is_pointed': transaction.is_pointed,
            'category': transaction.category_name or 'Non catégorisé',
            'status': transaction.status
        }

        # Pour les achats CB, récupérer les infos du reçu si disponible
        if transaction.source_type == 'card_purchase' and transaction.source_id:
            from app.models import CardPurchase
            card_purchase = CardPurchase.query.get(transaction.source_id)
            if card_purchase and card_purchase.receipt_image_data:
                movement['has_receipt'] = True
                movement['receipt_mime_type'] = card_purchase.receipt_image_mime_type
                movement['receipt_name'] = card_purchase.receipt_image_name
            else:
                movement['has_receipt'] = False
        else:
            movement['has_receipt'] = False

        # Pour les paiements en plusieurs fois, récupérer la progression
        if transaction.source_type == 'installment' and transaction.source_id:
            from app.models import InstallmentPayment
            installment = InstallmentPayment.query.get(transaction.source_id)
            if installment:
                movement['installments_paid'] = installment.installments_paid
                movement['number_of_installments'] = installment.number_of_installments

        movements.append(movement)

    # Calculer le solde progressif (du plus ancien au plus récent)
    balance = 0
    for movement in reversed(movements):
        if movement['is_positive']:
            balance += movement['amount']
        else:
            balance -= movement['amount']
        movement['balance'] = balance

    # Inverser à nouveau pour garder l'ordre du plus récent en haut
    movements.reverse()

    # Calculer les totaux
    total_revenues = sum(m['amount'] for m in movements if m['is_positive'])
    total_expenses = sum(m['amount'] for m in movements if not m['is_positive'])
    final_balance = total_revenues - total_expenses

    return render_template('balance.html',
                         movements=movements,
                         selected_month=selected_month,
                         selected_year=selected_year,
                         selected_status=selected_status,
                         total_revenues=round(total_revenues, 2),
                         total_expenses=round(total_expenses, 2),
                         final_balance=round(final_balance, 2),
                         now=datetime.utcnow())


@bp.route('/balance/toggle-point/<int:transaction_id>', methods=['POST'])
@login_required
def toggle_point(transaction_id):
    """Pointer/dépointer une transaction"""
    transaction = Transaction.query.get_or_404(transaction_id)

    # Vérifier que l'utilisateur est propriétaire de la transaction
    if transaction.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cette transaction.', 'danger')
        return redirect(url_for('main.balance'))

    # Basculer l'état de pointage
    transaction.is_pointed = not transaction.is_pointed
    db.session.commit()

    # Vérifier si on doit rediriger vers le dashboard
    redirect_to = request.form.get('redirect_to', 'balance')

    if redirect_to == 'dashboard':
        return redirect(url_for('main.dashboard'))

    # Retourner à la page balance avec les mêmes filtres
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    return redirect(url_for('main.balance', month=month, year=year))


@bp.route('/balance/mark-as-completed/<int:transaction_id>', methods=['POST'])
@login_required
def mark_as_completed(transaction_id):
    """Marquer une transaction comme complétée"""
    transaction = Transaction.query.get_or_404(transaction_id)

    # Vérifier que l'utilisateur est propriétaire de la transaction
    if transaction.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cette transaction.', 'danger')
        return redirect(url_for('main.balance'))

    # Passer le statut en completed
    old_status = transaction.status
    transaction.status = 'completed'
    db.session.commit()

    flash(f'Transaction "{transaction.name}" passée en statut complété.', 'success')

    # Retourner à la page balance avec les mêmes filtres
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    return redirect(url_for('main.balance', month=month, year=year))


@bp.route('/balance/mark-as-pending/<int:transaction_id>', methods=['POST'])
@login_required
def mark_as_pending(transaction_id):
    """Marquer une transaction comme en attente (repasser de completed à pending)"""
    transaction = Transaction.query.get_or_404(transaction_id)

    # Vérifier que l'utilisateur est propriétaire de la transaction
    if transaction.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cette transaction.', 'danger')
        return redirect(url_for('main.balance'))

    # Passer le statut en pending
    old_status = transaction.status
    transaction.status = 'pending'
    db.session.commit()

    flash(f'Transaction "{transaction.name}" repassée en statut en attente.', 'info')

    # Retourner à la page balance avec les mêmes filtres
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    return redirect(url_for('main.balance', month=month, year=year))


@bp.route('/balance/toggle-all-month', methods=['POST'])
@login_required
def toggle_all_month():
    """Pointer/dépointer toutes les transactions d'un mois"""
    from calendar import monthrange

    # Récupérer les paramètres de filtre
    month = request.form.get('month', type=int)
    year = request.form.get('year', type=int)
    status_filter = request.form.get('status', 'all')
    action = request.form.get('action', 'point')  # 'point' ou 'unpoint'

    if not month or not year:
        flash('Paramètres invalides.', 'danger')
        return redirect(url_for('main.balance'))

    # Calculer le premier et dernier jour du mois
    first_day = datetime(year, month, 1).date()
    last_day_num = monthrange(year, month)[1]
    last_day = datetime(year, month, last_day_num).date()

    # Construire la requête de base (transactions du mois, sauf les annulées)
    query = current_user.transactions.filter(
        Transaction.transaction_date >= first_day,
        Transaction.transaction_date <= last_day,
        Transaction.status != 'cancelled'
    )

    # Ajouter le filtre de statut si nécessaire
    if status_filter != 'all':
        query = query.filter(Transaction.status == status_filter)

    # Récupérer toutes les transactions
    transactions = query.all()

    # Pointer ou dépointer selon l'action
    count = 0
    if action == 'point':
        for transaction in transactions:
            if not transaction.is_pointed:
                transaction.is_pointed = True
                count += 1
    else:  # unpoint
        for transaction in transactions:
            if transaction.is_pointed:
                transaction.is_pointed = False
                count += 1

    db.session.commit()

    if action == 'point':
        flash(f'{count} transaction(s) pointée(s) avec succès.', 'success')
    else:
        flash(f'{count} transaction(s) dépointée(s) avec succès.', 'success')

    return redirect(url_for('main.balance', month=month, year=year, status=status_filter))


@bp.route('/balance/delete-transaction/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    """Supprimer/annuler une transaction spécifique sans supprimer l'objet source"""
    transaction = Transaction.query.get_or_404(transaction_id)

    # Vérifier que l'utilisateur est propriétaire de la transaction
    if transaction.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cette transaction.', 'danger')
        return redirect(url_for('main.balance'))

    # Marquer la transaction comme annulée (au lieu de la supprimer)
    transaction.status = 'cancelled'
    db.session.commit()

    flash(f'La transaction "{transaction.name}" a été annulée.', 'success')

    # Retourner à la page balance avec les mêmes filtres
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    return redirect(url_for('main.balance', month=month, year=year))


@bp.route('/balance/delete-transactions-bulk/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transactions_bulk(transaction_id):
    """Supprimer des transactions selon différents modes"""
    transaction = Transaction.query.get_or_404(transaction_id)

    # Vérifier que l'utilisateur est propriétaire de la transaction
    if transaction.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cette transaction.', 'danger')
        return redirect(url_for('main.balance'))

    delete_mode = request.args.get('delete_mode', 'single')
    source_id = transaction.source_id
    source_type = transaction.source_type
    transaction_date = transaction.transaction_date

    count = 0

    if delete_mode == 'single':
        # Supprimer uniquement cette transaction
        transaction.status = 'cancelled'
        count = 1
        db.session.commit()
        flash(f'La transaction a été annulée.', 'success')

    elif delete_mode == 'past':
        # Supprimer toutes les transactions passées (inclus celle-ci)
        past_transactions = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.source_id == source_id,
            Transaction.source_type == source_type,
            Transaction.transaction_date <= transaction_date,
            Transaction.status != 'cancelled'
        ).all()

        for t in past_transactions:
            t.status = 'cancelled'
            count += 1

        db.session.commit()
        flash(f'{count} transaction(s) passée(s) ont été annulée(s).', 'success')

    elif delete_mode == 'future':
        # Supprimer toutes les transactions futures (inclus celle-ci)
        future_transactions = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.source_id == source_id,
            Transaction.source_type == source_type,
            Transaction.transaction_date >= transaction_date,
            Transaction.status != 'cancelled'
        ).all()

        for t in future_transactions:
            t.status = 'cancelled'
            count += 1

        db.session.commit()
        flash(f'{count} transaction(s) future(s) ont été annulée(s).', 'success')

    elif delete_mode == 'all':
        # Supprimer toutes les transactions liées
        all_transactions = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.source_id == source_id,
            Transaction.source_type == source_type,
            Transaction.status != 'cancelled'
        ).all()

        for t in all_transactions:
            t.status = 'cancelled'
            count += 1

        db.session.commit()
        flash(f'{count} transaction(s) ont été annulée(s).', 'success')

    # Retourner à la page balance avec les mêmes filtres
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    return redirect(url_for('main.balance', month=month, year=year))


@bp.route('/notifications')
@login_required
def notifications():
    filter_type = request.args.get('filter', 'unread')  # 'unread', 'read', 'archived', 'all'

    if filter_type == 'archived':
        # Afficher uniquement les notifications archivées
        user_notifications = current_user.notifications.filter_by(
            archived=True
        ).order_by(
            Notification.created_at.desc()
        ).all()
    elif filter_type == 'read':
        # Afficher uniquement les notifications lues (non archivées)
        user_notifications = current_user.notifications.filter_by(
            is_read=True,
            archived=False
        ).order_by(
            Notification.created_at.desc()
        ).all()
    elif filter_type == 'all':
        # Afficher toutes les notifications
        user_notifications = current_user.notifications.order_by(
            Notification.created_at.desc()
        ).all()
    else:  # 'unread' par défaut
        # Afficher uniquement les notifications non lues
        user_notifications = current_user.notifications.filter_by(
            is_read=False,
            archived=False
        ).order_by(
            Notification.created_at.desc()
        ).all()

    return render_template('notifications.html',
                         notifications=user_notifications,
                         filter_type=filter_type)


@bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        return redirect(url_for('main.notifications'))

    notification.mark_as_read()

    # Récupérer le filtre actuel pour rediriger vers la même vue
    filter_type = request.args.get('filter', 'unread')
    return redirect(url_for('main.notifications', filter=filter_type))


@bp.route('/notifications/<int:notification_id>/delete', methods=['POST'])
@login_required
def delete_notification(notification_id):
    if not current_user.is_admin:
        flash('Vous n\'avez pas les permissions pour supprimer des notifications.', 'danger')
        return redirect(url_for('main.notifications'))

    notification = Notification.query.get_or_404(notification_id)
    db.session.delete(notification)
    db.session.commit()

    flash('La notification a été supprimée avec succès.', 'success')
    return redirect(url_for('main.notifications'))


@bp.route('/notifications/archive', methods=['POST'])
@login_required
def archive_notifications():
    notification_ids = request.form.getlist('notification_ids[]')

    if not notification_ids:
        flash('Veuillez sélectionner au moins une notification à archiver.', 'warning')
        return redirect(url_for('main.notifications'))

    archived_count = 0
    for notif_id in notification_ids:
        notification = Notification.query.get(int(notif_id))
        if notification and notification.user_id == current_user.id:
            notification.archive()
            archived_count += 1

    if archived_count > 0:
        flash(f'{archived_count} notification(s) archivée(s) avec succès.', 'success')
    else:
        flash('Aucune notification n\'a pu être archivée.', 'warning')

    return redirect(url_for('main.notifications'))


@bp.route('/notifications/mark-read', methods=['POST'])
@login_required
def mark_multiple_notifications_read():
    notification_ids = request.form.getlist('notification_ids[]')

    if not notification_ids:
        flash('Veuillez sélectionner au moins une notification à marquer comme lue.', 'warning')
        return redirect(url_for('main.notifications'))

    marked_count = 0
    for notif_id in notification_ids:
        notification = Notification.query.get(int(notif_id))
        if notification and notification.user_id == current_user.id and not notification.is_read:
            notification.mark_as_read()
            marked_count += 1

    if marked_count > 0:
        flash(f'{marked_count} notification(s) marquée(s) comme lue(s) avec succès.', 'success')
    else:
        flash('Aucune notification n\'a pu être marquée comme lue.', 'warning')

    return redirect(url_for('main.notifications'))


@bp.route('/notifications/delete-multiple', methods=['POST'])
@login_required
def delete_multiple_notifications():
    if not current_user.is_admin:
        flash('Vous n\'avez pas les permissions pour supprimer des notifications.', 'danger')
        return redirect(url_for('main.notifications'))

    notification_ids = request.form.getlist('notification_ids[]')

    if not notification_ids:
        flash('Veuillez sélectionner au moins une notification à supprimer.', 'warning')
        return redirect(url_for('main.notifications'))

    deleted_count = 0
    for notif_id in notification_ids:
        notification = Notification.query.get(int(notif_id))
        if notification:
            db.session.delete(notification)
            deleted_count += 1

    db.session.commit()

    if deleted_count > 0:
        flash(f'{deleted_count} notification(s) supprimée(s) avec succès.', 'success')
    else:
        flash('Aucune notification n\'a pu être supprimée.', 'warning')

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


@bp.route('/set-language/<lang>', methods=['POST'])
def set_language(lang):
    """Change la langue de l'interface utilisateur"""
    # Vérifier que la langue est supportée
    supported_languages = ['fr', 'en', 'es', 'it', 'de', 'pt']
    if lang not in supported_languages:
        return jsonify({'error': 'Unsupported language'}), 400

    # Si l'utilisateur est connecté, sauvegarder la préférence en base de données
    if current_user.is_authenticated:
        current_user.language = lang
        db.session.commit()

    # Sauvegarder également en session pour les utilisateurs non connectés
    session['language'] = lang

    return jsonify({'success': True, 'language': lang})
