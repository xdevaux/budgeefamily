"""
Routes pour gérer les chéquiers
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app import db
from app.models import Checkbook, Check, Bank, Transaction
from datetime import datetime

bp = Blueprint('checkbooks', __name__, url_prefix='/checkbooks')


@bp.route('/')
@login_required
def list_checkbooks():
    """Liste des chéquiers de l'utilisateur"""
    page = request.args.get('page', 1, type=int)
    filter_status = request.args.get('status', 'all')
    filter_bank = request.args.get('bank_id', type=int)

    query = current_user.checkbooks

    # Filter by status
    if filter_status == 'active':
        query = query.filter_by(status='active')
    elif filter_status == 'finished':
        query = query.filter_by(status='finished')

    # Filter by bank
    if filter_bank:
        query = query.filter_by(bank_id=filter_bank)

    checkbooks = query.order_by(Checkbook.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )

    # Get user's banks for filter dropdown
    banks = current_user.banks.filter_by(is_active=True).order_by(Bank.name).all()

    return render_template('checkbooks/list.html',
                         checkbooks=checkbooks,
                         banks=banks,
                         filter_status=filter_status,
                         filter_bank=filter_bank)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Ajouter un nouveau chéquier"""
    if request.method == 'POST':
        name = request.form.get('name')
        bank_id = request.form.get('bank_id', type=int)
        start_number = request.form.get('start_number', type=int)
        end_number = request.form.get('end_number', type=int)

        # Validation du numéro de départ
        if not start_number:
            flash(_('Le numéro du premier chèque est requis.'), 'danger')
            return redirect(url_for('checkbooks.add'))

        # Si end_number n'est pas fourni, calculer automatiquement (+25)
        if not end_number:
            end_number = start_number + 25

        # Validation
        if start_number >= end_number:
            flash(_('Le numéro de fin doit être supérieur au numéro de début.'), 'danger')
            return redirect(url_for('checkbooks.add'))

        checkbook = Checkbook(
            user_id=current_user.id,
            name=name,
            bank_id=bank_id if bank_id else None,
            start_number=start_number,
            end_number=end_number
        )

        db.session.add(checkbook)
        db.session.flush()  # Obtenir checkbook.id

        # Génération automatique de tous les chèques
        for check_num in range(start_number, end_number + 1):
            check = Check(
                user_id=current_user.id,
                checkbook_id=checkbook.id,
                check_number=check_num,
                amount=0.0,  # Placeholder
                currency='EUR',
                check_date=datetime.now().date(),
                status='available'
            )
            db.session.add(check)

        db.session.commit()

        flash(_('Chéquier "%(name)s" ajouté avec succès avec %(count)s chèques !', name=name, count=checkbook.total_checks()), 'success')
        return redirect(url_for('checkbooks.detail', checkbook_id=checkbook.id))

    # Récupérer les banques pour le formulaire
    banks = current_user.banks.filter_by(is_active=True).order_by(Bank.name).all()

    return render_template('checkbooks/add.html', banks=banks, now=datetime.now())


@bp.route('/<int:checkbook_id>')
@login_required
def detail(checkbook_id):
    """Détails d'un chéquier"""
    checkbook = Checkbook.query.get_or_404(checkbook_id)

    if checkbook.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce chéquier.'), 'danger')
        return redirect(url_for('checkbooks.list_checkbooks'))

    # Récupérer les chèques avec pagination
    page = request.args.get('page', 1, type=int)
    filter_status = request.args.get('status', 'used')  # Filtre par défaut sur "Utilisés"

    query = checkbook.checks

    if filter_status == 'available':
        query = query.filter_by(status='available')
    elif filter_status == 'used':
        query = query.filter_by(status='used')
    elif filter_status == 'cancelled':
        query = query.filter_by(status='cancelled')

    checks = query.order_by(Check.check_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template('checkbooks/detail.html',
                         checkbook=checkbook,
                         checks=checks,
                         filter_status=filter_status)


@bp.route('/<int:checkbook_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(checkbook_id):
    """Modifier un chéquier"""
    checkbook = Checkbook.query.get_or_404(checkbook_id)

    if checkbook.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce chéquier.'), 'danger')
        return redirect(url_for('checkbooks.list_checkbooks'))

    if request.method == 'POST':
        checkbook.name = request.form.get('name')
        checkbook.bank_id = request.form.get('bank_id', type=int) or None
        checkbook.updated_at = datetime.utcnow()

        db.session.commit()

        flash(_('Chéquier modifié avec succès !'), 'success')
        return redirect(url_for('checkbooks.detail', checkbook_id=checkbook.id))

    # Récupérer les banques pour le formulaire
    banks = current_user.banks.filter_by(is_active=True).order_by(Bank.name).all()

    return render_template('checkbooks/edit.html', checkbook=checkbook, banks=banks)


@bp.route('/<int:checkbook_id>/toggle', methods=['POST'])
@login_required
def toggle(checkbook_id):
    """Activer/Désactiver un chéquier"""
    checkbook = Checkbook.query.get_or_404(checkbook_id)

    if checkbook.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce chéquier.'), 'danger')
        return redirect(url_for('checkbooks.list_checkbooks'))

    checkbook.is_active = not checkbook.is_active
    db.session.commit()

    status = _('activé') if checkbook.is_active else _('désactivé')
    flash(_('Le chéquier "%(name)s" a été %(status)s.', name=checkbook.name, status=status), 'success')
    return redirect(url_for('checkbooks.list_checkbooks'))


@bp.route('/<int:checkbook_id>/delete', methods=['POST'])
@login_required
def delete(checkbook_id):
    """Supprimer un chéquier"""
    checkbook = Checkbook.query.get_or_404(checkbook_id)

    if checkbook.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce chéquier.'), 'danger')
        return redirect(url_for('checkbooks.list_checkbooks'))

    # Vérifier si des chèques sont associés
    if checkbook.checks.count() > 0:
        flash(_('Impossible de supprimer ce chéquier car il contient des chèques.'), 'warning')
        return redirect(url_for('checkbooks.detail', checkbook_id=checkbook_id))

    checkbook_name = checkbook.name
    db.session.delete(checkbook)
    db.session.commit()

    flash(_('Chéquier "%(name)s" supprimé avec succès !', name=checkbook_name), 'success')
    return redirect(url_for('checkbooks.list_checkbooks'))


@bp.route('/<int:checkbook_id>/archive', methods=['POST'])
@login_required
def archive(checkbook_id):
    """Archiver un chéquier"""
    checkbook = Checkbook.query.get_or_404(checkbook_id)

    if checkbook.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce chéquier.'), 'danger')
        return redirect(url_for('checkbooks.list_checkbooks'))

    checkbook.status = 'finished'
    checkbook.updated_at = datetime.utcnow()
    db.session.commit()

    flash(_('Le chéquier "%(name)s" a été archivé.', name=checkbook.name), 'success')
    return redirect(url_for('checkbooks.list_checkbooks'))


@bp.route('/<int:checkbook_id>/unarchive', methods=['POST'])
@login_required
def unarchive(checkbook_id):
    """Désarchiver un chéquier"""
    checkbook = Checkbook.query.get_or_404(checkbook_id)

    if checkbook.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce chéquier.'), 'danger')
        return redirect(url_for('checkbooks.list_checkbooks'))

    checkbook.status = 'active'
    checkbook.updated_at = datetime.utcnow()
    db.session.commit()

    flash(_('Le chéquier "%(name)s" a été désarchivé.', name=checkbook.name), 'success')
    return redirect(url_for('checkbooks.list_checkbooks'))


# Routes pour les chèques
@bp.route('/<int:checkbook_id>/checks/add', methods=['GET', 'POST'])
@login_required
def add_check(checkbook_id):
    """Utiliser un chèque disponible"""
    checkbook = Checkbook.query.get_or_404(checkbook_id)

    if checkbook.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce chéquier.'), 'danger')
        return redirect(url_for('checkbooks.list_checkbooks'))

    # Récupérer les chèques disponibles
    available_checks = checkbook.checks.filter_by(status='available').order_by(Check.check_number).all()

    if not available_checks:
        flash(_('Aucun chèque disponible dans ce chéquier.'), 'warning')
        return redirect(url_for('checkbooks.detail', checkbook_id=checkbook_id))

    if request.method == 'POST':
        check_id = request.form.get('check_id', type=int)
        amount = request.form.get('amount', type=float)
        payee = request.form.get('payee')
        description = request.form.get('description')
        check_date_str = request.form.get('check_date')
        action = request.form.get('action')  # 'use' ou 'cancel'

        check = Check.query.get_or_404(check_id)

        # Vérifier que le chèque est disponible
        if check.status != 'available' or check.checkbook_id != checkbook_id:
            flash(_('Ce chèque n\'est pas disponible.'), 'danger')
            return redirect(url_for('checkbooks.add_check', checkbook_id=checkbook_id))

        check_date = datetime.strptime(check_date_str, '%Y-%m-%d').date() if check_date_str else datetime.now().date()

        # Mettre à jour le chèque
        check.amount = amount
        check.payee = payee
        check.description = description
        check.check_date = check_date
        check.updated_at = datetime.utcnow()

        if action == 'cancel':
            check.status = 'cancelled'
            flash(_('Chèque #%(number)s annulé avec succès !', number=check.check_number), 'success')
        else:
            check.status = 'used'

            # Créer la transaction dans la balance
            transaction = Transaction(
                user_id=current_user.id,
                transaction_date=check_date,
                transaction_type='check',
                source_id=check.id,
                source_type='check',
                name=f'Chèque #{check.check_number} - {payee}',
                description=description,
                amount=amount,
                currency='EUR',
                is_positive=False,
                category_name='Chèques',
                status='completed'
            )
            db.session.add(transaction)
            flash(_('Chèque #%(number)s utilisé avec succès !', number=check.check_number), 'success')

        db.session.commit()

        # Auto-archivage si tous les chèques sont consommés
        checkbook.auto_finish_if_complete()

        return redirect(url_for('checkbooks.detail', checkbook_id=checkbook_id))

    return render_template('checkbooks/add_check.html',
                         checkbook=checkbook,
                         available_checks=available_checks,
                         now=datetime.now())


@bp.route('/checks/<int:check_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_check(check_id):
    """Modifier un chèque"""
    check = Check.query.get_or_404(check_id)

    if check.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce chèque.'), 'danger')
        return redirect(url_for('checkbooks.list_checkbooks'))

    # Bloquer l'édition des chèques 'available' (non utilisés)
    if check.status == 'available':
        flash(_('Vous ne pouvez pas modifier un chèque non utilisé. Veuillez l\'utiliser d\'abord.'), 'warning')
        return redirect(url_for('checkbooks.detail', checkbook_id=check.checkbook_id))

    if request.method == 'POST':
        old_status = check.status

        check.amount = request.form.get('amount', type=float)
        check.currency = request.form.get('currency', 'EUR')
        check.payee = request.form.get('payee')
        check.description = request.form.get('description')
        check_date_str = request.form.get('check_date')
        check.check_date = datetime.strptime(check_date_str, '%Y-%m-%d').date() if check_date_str else check.check_date
        check.status = request.form.get('status')
        check.updated_at = datetime.utcnow()

        # Gérer la transaction associée
        if old_status != 'used' and check.status == 'used':
            # Créer une nouvelle transaction
            transaction = Transaction(
                user_id=current_user.id,
                transaction_date=check.check_date,
                transaction_type='check',
                source_id=check.id,
                source_type='check',
                name=f'Chèque #{check.check_number} - {check.payee}',
                description=check.description,
                amount=check.amount,
                currency=check.currency,
                is_positive=False,
                category_name='Chèques',
                status='completed'
            )
            db.session.add(transaction)
        elif old_status == 'used' and check.status != 'used':
            # Annuler la transaction existante
            transaction = Transaction.query.filter_by(
                source_id=check.id,
                source_type='check'
            ).first()
            if transaction:
                transaction.status = 'cancelled'

        db.session.commit()

        # Auto-archivage si tous les chèques sont consommés
        checkbook = Checkbook.query.get(check.checkbook_id)
        checkbook.auto_finish_if_complete()

        flash(_('Chèque #%(number)s modifié avec succès !', number=check.check_number), 'success')
        return redirect(url_for('checkbooks.detail', checkbook_id=check.checkbook_id))

    return render_template('checkbooks/edit_check.html', check=check)


@bp.route('/check/<int:check_id>/detail-partial')
@login_required
def check_detail_partial(check_id):
    """Retourne un template partiel avec les détails du chèque pour affichage en modale"""
    check = Check.query.get_or_404(check_id)

    if check.user_id != current_user.id:
        return '<div class="alert alert-danger">Accès non autorisé</div>', 403

    return render_template('checkbooks/check_detail_partial.html', check=check)


@bp.route('/checks/<int:check_id>/delete', methods=['POST'])
@login_required
def delete_check(check_id):
    """Remettre un chèque disponible"""
    check = Check.query.get_or_404(check_id)

    if check.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce chèque.'), 'danger')
        return redirect(url_for('checkbooks.list_checkbooks'))

    checkbook_id = check.checkbook_id
    check_number = check.check_number

    # Annuler la transaction associée si elle existe
    transaction = Transaction.query.filter_by(
        source_id=check.id,
        source_type='check'
    ).first()
    if transaction:
        transaction.status = 'cancelled'

    # Remettre le chèque à l'état disponible au lieu de le supprimer
    check.status = 'available'
    check.amount = 0.0
    check.payee = None
    check.description = None
    check.check_date = datetime.now().date()
    check.updated_at = datetime.utcnow()

    db.session.commit()

    flash(_('Chèque #%(number)s est à nouveau disponible !', number=check_number), 'success')
    return redirect(url_for('checkbooks.detail', checkbook_id=checkbook_id))
