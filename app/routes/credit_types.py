from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import CreditType

bp = Blueprint('credit_types', __name__, url_prefix='/credit-types')


@bp.route('/')
@login_required
def list():
    """Liste tous les types de crédits (globaux + personnalisés de l'utilisateur)"""
    # Types globaux (par défaut)
    global_types = CreditType.query.filter_by(user_id=None, is_active=True).order_by(CreditType.name).all()

    # Types personnalisés de l'utilisateur
    custom_types = current_user.custom_credit_types.order_by(CreditType.name).all()

    return render_template('credit_types/list.html',
                         global_types=global_types,
                         custom_types=custom_types)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Ajouter un type de crédit personnalisé"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        icon = request.form.get('icon', 'fa-circle')
        color = request.form.get('color', '#6c757d')

        # Vérifier qu'un type avec ce nom n'existe pas déjà pour cet utilisateur
        existing = CreditType.query.filter_by(user_id=current_user.id, name=name).first()
        if existing:
            flash(f'Un type de crédit "{name}" existe déjà dans vos types personnalisés.', 'warning')
            return redirect(url_for('credit_types.add'))

        credit_type = CreditType(
            user_id=current_user.id,
            name=name,
            description=description,
            icon=icon,
            color=color
        )

        db.session.add(credit_type)
        db.session.commit()

        flash(f'Le type de crédit "{name}" a été créé avec succès !', 'success')
        return redirect(url_for('credit_types.list'))

    return render_template('credit_types/add.html')


@bp.route('/<int:type_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(type_id):
    """Modifier un type de crédit personnalisé"""
    credit_type = CreditType.query.get_or_404(type_id)

    # Vérifier que c'est bien un type de l'utilisateur
    if credit_type.user_id != current_user.id:
        flash('Vous ne pouvez modifier que vos propres types de crédits.', 'danger')
        return redirect(url_for('credit_types.list'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        icon = request.form.get('icon', 'fa-circle')
        color = request.form.get('color', '#6c757d')

        # Vérifier qu'un autre type avec ce nom n'existe pas déjà pour cet utilisateur
        existing = CreditType.query.filter_by(user_id=current_user.id, name=name).filter(CreditType.id != type_id).first()
        if existing:
            flash(f'Un type de crédit "{name}" existe déjà dans vos types personnalisés.', 'warning')
            return render_template('credit_types/edit.html', credit_type=credit_type)

        credit_type.name = name
        credit_type.description = description
        credit_type.icon = icon
        credit_type.color = color

        db.session.commit()

        flash(f'Le type de crédit "{name}" a été mis à jour avec succès !', 'success')
        return redirect(url_for('credit_types.list'))

    return render_template('credit_types/edit.html', credit_type=credit_type)


@bp.route('/<int:type_id>/delete', methods=['POST'])
@login_required
def delete(type_id):
    """Supprimer un type de crédit personnalisé"""
    credit_type = CreditType.query.get_or_404(type_id)

    # Vérifier que c'est bien un type de l'utilisateur
    if credit_type.user_id != current_user.id:
        flash('Vous ne pouvez supprimer que vos propres types de crédits.', 'danger')
        return redirect(url_for('credit_types.list'))

    # Vérifier qu'aucun crédit n'utilise ce type
    if credit_type.credits.count() > 0:
        flash(f'Impossible de supprimer le type "{credit_type.name}" car il est utilisé par {credit_type.credits.count()} crédit(s).', 'danger')
        return redirect(url_for('credit_types.list'))

    type_name = credit_type.name
    db.session.delete(credit_type)
    db.session.commit()

    flash(f'Le type de crédit "{type_name}" a été supprimé avec succès !', 'success')
    return redirect(url_for('credit_types.list'))


@bp.route('/<int:type_id>/toggle', methods=['POST'])
@login_required
def toggle(type_id):
    """Activer/désactiver un type de crédit personnalisé"""
    credit_type = CreditType.query.get_or_404(type_id)

    # Vérifier que c'est bien un type de l'utilisateur
    if credit_type.user_id != current_user.id:
        flash('Vous ne pouvez modifier que vos propres types de crédits.', 'danger')
        return redirect(url_for('credit_types.list'))

    credit_type.is_active = not credit_type.is_active
    db.session.commit()

    status = 'activé' if credit_type.is_active else 'désactivé'
    flash(f'Le type de crédit "{credit_type.name}" a été {status}.', 'success')
    return redirect(url_for('credit_types.list'))
