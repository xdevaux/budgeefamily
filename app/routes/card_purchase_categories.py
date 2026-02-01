from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app import db
from app.models import Category
from datetime import datetime

bp = Blueprint('card_purchase_categories', __name__, url_prefix='/card-purchase-categories')


@bp.route('/')
@login_required
def list_categories():
    """Liste des catégories pour achats CB"""
    # Catégories globales pour achats CB
    global_categories = Category.query.filter_by(
        user_id=None,
        is_active=True
    ).filter(
        db.or_(
            Category.category_type == 'card_purchase',
            Category.category_type == 'all'
        )
    ).order_by(Category.name).all()

    # Catégories personnalisées de l'utilisateur pour achats CB
    user_categories = Category.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).filter(
        db.or_(
            Category.category_type == 'card_purchase',
            Category.category_type == 'all'
        )
    ).order_by(Category.name).all()

    return render_template('card_purchase_categories/list.html',
                         global_categories=global_categories,
                         user_categories=user_categories)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_category():
    """Ajouter une catégorie pour achats CB"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        color = request.form.get('color', '#6c757d')
        icon = request.form.get('icon')

        if not name:
            flash(_('Le nom de la catégorie est obligatoire.'), 'danger')
            return redirect(url_for('card_purchase_categories.add_category'))

        # Créer la catégorie
        category = Category(
            user_id=current_user.id,
            name=name,
            description=description,
            color=color,
            icon=icon,
            category_type='card_purchase',  # Spécifique aux achats CB
            is_active=True
        )

        db.session.add(category)
        db.session.commit()

        flash(_('La catégorie "%(name)s" a été créée avec succès.', name=name), 'success')
        return redirect(url_for('card_purchase_categories.list_categories'))

    return render_template('card_purchase_categories/add.html')


@bp.route('/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    """Modifier une catégorie"""
    category = Category.query.get_or_404(category_id)

    # Vérifier que l'utilisateur est propriétaire
    if category.user_id != current_user.id:
        flash(_('Vous ne pouvez modifier que vos propres catégories.'), 'danger')
        return redirect(url_for('card_purchase_categories.list_categories'))

    if request.method == 'POST':
        category.name = request.form.get('name')
        category.description = request.form.get('description')
        category.color = request.form.get('color', '#6c757d')
        category.icon = request.form.get('icon')
        category.updated_at = datetime.utcnow()

        db.session.commit()

        flash(_('La catégorie "%(name)s" a été modifiée.', name=category.name), 'success')
        return redirect(url_for('card_purchase_categories.list_categories'))

    return render_template('card_purchase_categories/edit.html', category=category)


@bp.route('/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    """Supprimer une catégorie"""
    category = Category.query.get_or_404(category_id)

    # Vérifier que l'utilisateur est propriétaire
    if category.user_id != current_user.id:
        flash(_('Vous ne pouvez supprimer que vos propres catégories.'), 'danger')
        return redirect(url_for('card_purchase_categories.list_categories'))

    # Désactiver au lieu de supprimer
    category.is_active = False
    db.session.commit()

    flash(_('La catégorie "%(name)s" a été supprimée.', name=category.name), 'success')
    return redirect(url_for('card_purchase_categories.list_categories'))
