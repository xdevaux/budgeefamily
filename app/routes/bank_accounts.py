"""
Routes pour gérer les comptes bancaires
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app import db
from app.models import BankAccount, Bank
from datetime import datetime

bp = Blueprint('bank_accounts', __name__, url_prefix='/bank-accounts')


# Types de comptes bancaires
def get_account_types():
    """Retourne les types de comptes avec traduction"""
    return [
        ('checking', _('Compte courant'), 'fa-money-check-alt', '#10b981'),
        ('savings', _('Compte épargne'), 'fa-piggy-bank', '#f59e0b'),
        ('business', _('Compte professionnel'), 'fa-briefcase', '#6366f1'),
        ('other', _('Autre'), 'fa-wallet', '#6c757d'),
    ]


def get_account_type_label(account_type_code):
    """Retourne le libellé traduit d'un type de compte"""
    types_dict = {code: label for code, label, icon, color in get_account_types()}
    return types_dict.get(account_type_code, account_type_code)


@bp.route('/add/<int:bank_id>', methods=['GET', 'POST'])
@login_required
def add(bank_id):
    """Ajouter un nouveau compte bancaire"""
    bank = Bank.query.get_or_404(bank_id)

    if bank.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à cette banque.'), 'danger')
        return redirect(url_for('banks.list_banks'))

    if request.method == 'POST':
        name = request.form.get('name')
        account_type = request.form.get('account_type', 'checking')
        account_number = request.form.get('account_number')
        iban = request.form.get('iban')
        bic = request.form.get('bic')
        currency = request.form.get('currency', 'EUR')
        opening_balance_str = request.form.get('opening_balance')
        opening_balance = float(opening_balance_str) if opening_balance_str else 0.0
        notes = request.form.get('notes')
        is_default = request.form.get('is_default') == 'on'

        # Si ce compte doit être le compte par défaut, désactiver les autres
        if is_default:
            BankAccount.query.filter_by(
                bank_id=bank_id,
                user_id=current_user.id
            ).update({'is_default': False})

        account = BankAccount(
            user_id=current_user.id,
            bank_id=bank_id,
            name=name,
            account_type=account_type,
            account_number=account_number,
            iban=iban,
            bic=bic,
            currency=currency,
            opening_balance=opening_balance,
            notes=notes,
            is_default=is_default
        )

        db.session.add(account)
        db.session.commit()

        flash(_('Compte "%(name)s" ajouté avec succès !', name=name), 'success')
        return redirect(url_for('banks.detail', bank_id=bank_id))

    return render_template('bank_accounts/add.html',
                         bank=bank,
                         account_types=get_account_types())


@bp.route('/<int:account_id>')
@login_required
def detail(account_id):
    """Détails d'un compte bancaire"""
    account = BankAccount.query.get_or_404(account_id)

    if account.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce compte.'), 'danger')
        return redirect(url_for('banks.list_banks'))

    return render_template('bank_accounts/detail.html',
                         account=account,
                         get_account_type_label=get_account_type_label)


@bp.route('/<int:account_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(account_id):
    """Modifier un compte bancaire"""
    account = BankAccount.query.get_or_404(account_id)

    if account.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce compte.'), 'danger')
        return redirect(url_for('banks.list_banks'))

    if request.method == 'POST':
        account.name = request.form.get('name')
        account.account_type = request.form.get('account_type', 'checking')
        account.account_number = request.form.get('account_number')
        account.iban = request.form.get('iban')
        account.bic = request.form.get('bic')
        account.currency = request.form.get('currency', 'EUR')
        opening_balance_str = request.form.get('opening_balance')
        account.opening_balance = float(opening_balance_str) if opening_balance_str else 0.0
        account.notes = request.form.get('notes')
        is_default = request.form.get('is_default') == 'on'

        # Si ce compte doit être le compte par défaut, désactiver les autres
        if is_default and not account.is_default:
            BankAccount.query.filter_by(
                bank_id=account.bank_id,
                user_id=current_user.id
            ).filter(BankAccount.id != account.id).update({'is_default': False})

        account.is_default = is_default
        account.updated_at = datetime.utcnow()

        db.session.commit()

        flash(_('Compte modifié avec succès !'), 'success')
        return redirect(url_for('banks.detail', bank_id=account.bank_id))

    return render_template('bank_accounts/edit.html',
                         account=account,
                         account_types=get_account_types())


@bp.route('/<int:account_id>/toggle', methods=['POST'])
@login_required
def toggle(account_id):
    """Activer/Désactiver un compte bancaire"""
    account = BankAccount.query.get_or_404(account_id)

    if account.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce compte.'), 'danger')
        return redirect(url_for('banks.list_banks'))

    account.is_active = not account.is_active
    db.session.commit()

    status = _('activé') if account.is_active else _('désactivé')
    flash(_('Le compte "%(name)s" a été %(status)s.', name=account.name, status=status), 'success')
    return redirect(url_for('banks.detail', bank_id=account.bank_id))


@bp.route('/<int:account_id>/set-default', methods=['POST'])
@login_required
def set_default(account_id):
    """Définir comme compte par défaut"""
    account = BankAccount.query.get_or_404(account_id)

    if account.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce compte.'), 'danger')
        return redirect(url_for('banks.list_banks'))

    # Désactiver tous les autres comptes par défaut de cette banque
    BankAccount.query.filter_by(
        bank_id=account.bank_id,
        user_id=current_user.id
    ).update({'is_default': False})

    # Activer celui-ci
    account.is_default = True
    db.session.commit()

    flash(_('Compte par défaut défini.'), 'success')
    return redirect(url_for('banks.detail', bank_id=account.bank_id))


@bp.route('/<int:account_id>/delete', methods=['POST'])
@login_required
def delete(account_id):
    """Supprimer un compte bancaire"""
    account = BankAccount.query.get_or_404(account_id)

    if account.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce compte.'), 'danger')
        return redirect(url_for('banks.list_banks'))

    bank_id = account.bank_id
    account_name = account.name

    # TODO: Ajouter vérification si le compte est utilisé par des transactions
    # if account.transactions.count() > 0:
    #     flash(_('Impossible de supprimer ce compte car il est utilisé par des transactions.'), 'warning')
    #     return redirect(url_for('banks.detail', bank_id=bank_id))

    db.session.delete(account)
    db.session.commit()

    flash(_('Compte "%(name)s" supprimé avec succès !', name=account_name), 'success')
    return redirect(url_for('banks.detail', bank_id=bank_id))
