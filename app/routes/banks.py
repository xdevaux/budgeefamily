"""
Routes pour gérer les banques
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.models import Bank

bp = Blueprint('banks', __name__, url_prefix='/banks')


@bp.route('/')
@login_required
def list():
    """Liste des banques de l'utilisateur"""
    banks = Bank.query.filter_by(user_id=current_user.id).order_by(Bank.name).all()
    return render_template('banks/list.html', banks=banks)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Ajouter une nouvelle banque"""
    if request.method == 'POST':
        bank = Bank(
            user_id=current_user.id,
            name=request.form.get('name'),
            address=request.form.get('address'),
            postal_code=request.form.get('postal_code'),
            city=request.form.get('city'),
            country=request.form.get('country'),
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            website=request.form.get('website'),
            account_number=request.form.get('account_number'),
            iban=request.form.get('iban'),
            bic=request.form.get('bic'),
            notes=request.form.get('notes')
        )

        db.session.add(bank)
        db.session.commit()

        flash('Banque ajoutée avec succès !', 'success')
        return redirect(url_for('banks.list'))

    return render_template('banks/add.html')


@bp.route('/<int:bank_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(bank_id):
    """Modifier une banque"""
    bank = Bank.query.get_or_404(bank_id)

    if bank.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cette banque.', 'danger')
        return redirect(url_for('banks.list'))

    if request.method == 'POST':
        bank.name = request.form.get('name')
        bank.address = request.form.get('address')
        bank.postal_code = request.form.get('postal_code')
        bank.city = request.form.get('city')
        bank.country = request.form.get('country')
        bank.phone = request.form.get('phone')
        bank.email = request.form.get('email')
        bank.website = request.form.get('website')
        bank.account_number = request.form.get('account_number')
        bank.iban = request.form.get('iban')
        bank.bic = request.form.get('bic')
        bank.notes = request.form.get('notes')
        bank.updated_at = datetime.utcnow()

        db.session.commit()

        flash('Banque modifiée avec succès !', 'success')
        return redirect(url_for('banks.list'))

    return render_template('banks/edit.html', bank=bank)


@bp.route('/<int:bank_id>/delete', methods=['POST'])
@login_required
def delete(bank_id):
    """Supprimer une banque"""
    bank = Bank.query.get_or_404(bank_id)

    if bank.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cette banque.', 'danger')
        return redirect(url_for('banks.list'))

    # Vérifier si la banque est utilisée par des crédits
    if bank.credits.count() > 0:
        flash('Impossible de supprimer cette banque car elle est utilisée par des crédits.', 'warning')
        return redirect(url_for('banks.list'))

    db.session.delete(bank)
    db.session.commit()

    flash('Banque supprimée avec succès !', 'success')
    return redirect(url_for('banks.list'))


@bp.route('/api/list')
@login_required
def api_list():
    """API pour récupérer la liste des banques (pour les selects)"""
    banks = Bank.query.filter_by(user_id=current_user.id, is_active=True).order_by(Bank.name).all()
    return jsonify([{
        'id': bank.id,
        'name': bank.name
    } for bank in banks])
