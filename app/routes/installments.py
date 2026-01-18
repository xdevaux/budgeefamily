from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import InstallmentPayment, Category, CreditType, Notification
from app.utils.transactions import generate_future_transactions, update_future_transactions, cancel_future_transactions
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

bp = Blueprint('installments', __name__, url_prefix='/installments')


@bp.route('/')
@login_required
def list():
    """Liste tous les paiements en plusieurs fois de l'utilisateur"""
    active_payments = current_user.installment_payments.filter_by(is_active=True).order_by(
        InstallmentPayment.next_payment_date.asc()
    ).all()

    completed_payments = current_user.installment_payments.filter_by(is_completed=True).order_by(
        InstallmentPayment.completed_at.desc()
    ).all()

    # Calculer les statistiques
    total_remaining = sum(payment.calculate_remaining_amount() for payment in active_payments)
    total_monthly = sum(payment.installment_amount for payment in active_payments)

    return render_template('installments/list.html',
                         active_payments=active_payments,
                         completed_payments=completed_payments,
                         total_remaining=total_remaining,
                         total_monthly=total_monthly)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Ajouter un nouveau paiement en plusieurs fois"""
    if request.method == 'POST':
        # Vérifier si l'utilisateur peut ajouter un paiement en plusieurs fois
        if not current_user.can_add_installment_payment():
            flash('Vous avez atteint la limite de paiements en plusieurs fois pour le plan gratuit. Passez au plan Premium pour ajouter des paiements illimités.', 'warning')
            return redirect(url_for('installments.list'))

        name = request.form.get('name')
        description = request.form.get('description')
        merchant = request.form.get('merchant')
        total_amount = float(request.form.get('total_amount'))
        number_of_installments = int(request.form.get('number_of_installments'))
        has_fees = request.form.get('has_fees') == 'on'
        fees_amount = float(request.form.get('fees_amount', 0))
        provider = request.form.get('provider')
        product_category = request.form.get('product_category') or None
        credit_type_id = request.form.get('credit_type_id') or None
        start_date_str = request.form.get('start_date')
        currency = request.form.get('currency', 'EUR')

        # Convertir la date
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

        # Calculer le montant de chaque mensualité
        if has_fees:
            total_with_fees = total_amount + fees_amount
        else:
            total_with_fees = total_amount

        installment_amount = total_with_fees / number_of_installments

        # Calculer la date de fin
        end_date = start_date + relativedelta(months=number_of_installments - 1)

        # Créer le paiement
        payment = InstallmentPayment(
            user_id=current_user.id,
            name=name,
            description=description,
            merchant=merchant,
            total_amount=total_amount,
            installment_amount=round(installment_amount, 2),
            number_of_installments=number_of_installments,
            has_fees=has_fees,
            fees_amount=fees_amount,
            provider=provider,
            product_category=product_category,
            credit_type_id=credit_type_id,
            start_date=start_date,
            next_payment_date=start_date,
            end_date=end_date,
            currency=currency
        )

        db.session.add(payment)
        db.session.commit()

        # Générer les transactions futures (nombre de mensualités restantes)
        generate_future_transactions(payment, 'installment', number_of_installments)
        db.session.commit()

        # Créer une notification
        notification = Notification(
            user_id=current_user.id,
            installment_payment_id=payment.id,
            created_by_user_id=current_user.id,
            type='installment_added',
            title='Nouveau paiement en plusieurs fois ajouté',
            message=f'Votre paiement en plusieurs fois "{name}" a été ajouté avec succès. Montant: {installment_amount:.2f}€/mois sur {number_of_installments} mois.'
        )
        db.session.add(notification)
        db.session.commit()

        # Envoyer un email de notification si activé
        from app.utils.email import send_notification_email
        send_notification_email(current_user, notification)

        flash(f'Le paiement en plusieurs fois "{name}" a été ajouté avec succès.', 'success')
        return redirect(url_for('installments.list'))

    # GET - Afficher le formulaire
    credit_types = CreditType.query.filter(
        db.or_(CreditType.user_id == current_user.id, CreditType.user_id.is_(None))
    ).order_by(CreditType.name).all()

    return render_template('installments/add.html',
                         credit_types=credit_types,
                         now=datetime.now())


@bp.route('/<int:payment_id>')
@login_required
def detail(payment_id):
    """Détails d'un paiement en plusieurs fois"""
    payment = InstallmentPayment.query.get_or_404(payment_id)

    if payment.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce paiement.', 'danger')
        return redirect(url_for('installments.list'))

    return render_template('installments/detail.html', payment=payment)


@bp.route('/<int:payment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(payment_id):
    """Modifier un paiement en plusieurs fois"""
    payment = InstallmentPayment.query.get_or_404(payment_id)

    if payment.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce paiement.', 'danger')
        return redirect(url_for('installments.list'))

    if request.method == 'POST':
        payment.name = request.form.get('name')
        payment.description = request.form.get('description')
        payment.merchant = request.form.get('merchant')
        payment.provider = request.form.get('provider')
        payment.product_category = request.form.get('product_category') or None
        payment.credit_type_id = request.form.get('credit_type_id') or None

        db.session.commit()

        # Mettre à jour les transactions futures
        update_future_transactions(payment, 'installment')
        db.session.commit()

        flash('Le paiement a été mis à jour avec succès.', 'success')
        return redirect(url_for('installments.detail', payment_id=payment.id))

    credit_types = CreditType.query.filter(
        db.or_(CreditType.user_id == current_user.id, CreditType.user_id.is_(None))
    ).order_by(CreditType.name).all()

    return render_template('installments/edit.html',
                         payment=payment,
                         credit_types=credit_types)


@bp.route('/<int:payment_id>/delete', methods=['POST'])
@login_required
def delete(payment_id):
    """Supprimer un paiement en plusieurs fois"""
    payment = InstallmentPayment.query.get_or_404(payment_id)

    if payment.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce paiement.', 'danger')
        return redirect(url_for('installments.list'))

    name = payment.name

    # Annuler les transactions futures avant suppression
    cancel_future_transactions(payment.id, 'installment')

    db.session.delete(payment)
    db.session.commit()

    flash(f'Le paiement "{name}" a été supprimé avec succès.', 'success')
    return redirect(url_for('installments.list'))


@bp.route('/<int:payment_id>/process', methods=['POST'])
@login_required
def process(payment_id):
    """Traiter un paiement manuel"""
    payment = InstallmentPayment.query.get_or_404(payment_id)

    if payment.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce paiement.', 'danger')
        return redirect(url_for('installments.list'))

    if payment.process_payment():
        flash('Paiement traité avec succès !', 'success')
    else:
        flash('Ce paiement est déjà terminé.', 'warning')

    return redirect(url_for('installments.detail', payment_id=payment.id))
