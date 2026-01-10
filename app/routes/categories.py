from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import Category
import os
from config import Config
import base64
import mimetypes

bp = Blueprint('categories', __name__, url_prefix='/categories')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/')
@login_required
def list():
    """Liste toutes les catégories (globales + personnalisées de l'utilisateur)"""
    # Catégories globales (par défaut) - toujours actives et non masquées
    all_global_categories = Category.query.filter_by(user_id=None, is_active=True).order_by(Category.name).all()

    # Filtrer les catégories masquées par l'utilisateur
    hidden_ids = [cat.id for cat in current_user.hidden_categories_list]
    global_categories = [cat for cat in all_global_categories if cat.id not in hidden_ids]

    # Catégories personnalisées de l'utilisateur (actives ET inactives)
    custom_categories = current_user.custom_categories.order_by(Category.name).all()

    return render_template('categories/list.html',
                         global_categories=global_categories,
                         custom_categories=custom_categories)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Ajouter une catégorie personnalisée"""
    # Vérifier que l'utilisateur peut créer une catégorie
    if not current_user.can_create_custom_category():
        if current_user.is_premium():
            flash('Vous avez atteint la limite de catégories personnalisées.', 'warning')
        else:
            count = current_user.get_custom_categories_count()
            flash(f'Vous avez atteint la limite de 5 catégories personnalisées pour le plan gratuit ({count}/5). Passez au plan Premium pour créer un nombre illimité de catégories.', 'warning')
        return redirect(url_for('categories.list'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        color = request.form.get('color', '#6c757d')
        icon = request.form.get('icon')
        website_url = request.form.get('website_url')

        # Vérifier si l'utilisateur a déjà une catégorie avec ce nom
        existing = current_user.custom_categories.filter_by(name=name).first()
        if existing:
            flash(f'Vous avez déjà une catégorie nommée "{name}".', 'danger')
            return redirect(url_for('categories.add'))

        # Gérer l'upload du logo - stockage en base de données
        logo_data = None
        logo_mime_type = None
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename and allowed_file(file.filename):
                # Lire le fichier et le convertir en base64
                file_bytes = file.read()
                logo_data = base64.b64encode(file_bytes).decode('utf-8')

                # Déterminer le MIME type
                mime_type, _ = mimetypes.guess_type(file.filename)
                if mime_type:
                    logo_mime_type = mime_type
                else:
                    # Par défaut, PNG
                    logo_mime_type = 'image/png'

        # Créer la catégorie
        category = Category(
            user_id=current_user.id,
            name=name,
            description=description,
            color=color,
            icon=icon,
            website_url=website_url,
            logo_data=logo_data,
            logo_mime_type=logo_mime_type
        )

        db.session.add(category)
        db.session.commit()

        flash(f'La catégorie "{name}" a été créée avec succès !', 'success')
        return redirect(url_for('categories.list'))

    return render_template('categories/add.html')


@bp.route('/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(category_id):
    """Modifier une catégorie personnalisée"""
    # Vérifier que l'utilisateur a le plan Premium
    if not current_user.can_create_custom_category():
        flash('La modification de catégories personnalisées est réservée aux utilisateurs Premium.', 'warning')
        return redirect(url_for('main.pricing'))

    category = Category.query.get_or_404(category_id)

    # Vérifier que c'est bien une catégorie de l'utilisateur
    if category.user_id != current_user.id:
        flash('Vous ne pouvez modifier que vos propres catégories.', 'danger')
        return redirect(url_for('categories.list'))

    if request.method == 'POST':
        name = request.form.get('name')

        # Vérifier les doublons (sauf la catégorie actuelle)
        existing = current_user.custom_categories.filter(
            Category.name == name,
            Category.id != category_id
        ).first()

        if existing:
            flash(f'Vous avez déjà une catégorie nommée "{name}".', 'danger')
            return redirect(url_for('categories.edit', category_id=category_id))

        category.name = name
        category.description = request.form.get('description')
        category.color = request.form.get('color', '#6c757d')
        category.icon = request.form.get('icon')
        category.website_url = request.form.get('website_url')

        # Gérer l'upload du nouveau logo - stockage en base de données
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename and allowed_file(file.filename):
                # Lire le fichier et le convertir en base64
                file_bytes = file.read()
                category.logo_data = base64.b64encode(file_bytes).decode('utf-8')

                # Déterminer le MIME type
                mime_type, _ = mimetypes.guess_type(file.filename)
                if mime_type:
                    category.logo_mime_type = mime_type
                else:
                    # Par défaut, PNG
                    category.logo_mime_type = 'image/png'

        db.session.commit()

        flash(f'La catégorie "{category.name}" a été mise à jour.', 'success')
        return redirect(url_for('categories.list'))

    return render_template('categories/edit.html', category=category)


@bp.route('/<int:category_id>/delete', methods=['POST'])
@login_required
def delete(category_id):
    """Supprimer une catégorie personnalisée"""
    # Vérifier que l'utilisateur a le plan Premium
    if not current_user.can_create_custom_category():
        flash('La suppression de catégories personnalisées est réservée aux utilisateurs Premium.', 'warning')
        return redirect(url_for('main.pricing'))

    category = Category.query.get_or_404(category_id)

    # Vérifier que c'est bien une catégorie de l'utilisateur
    if category.user_id != current_user.id:
        flash('Vous ne pouvez supprimer que vos propres catégories.', 'danger')
        return redirect(url_for('categories.list'))

    # Vérifier si des abonnements utilisent cette catégorie
    subscriptions_count = category.subscriptions.count()
    if subscriptions_count > 0:
        flash(f'Impossible de supprimer cette catégorie car {subscriptions_count} abonnement(s) l\'utilisent.', 'warning')
        return redirect(url_for('categories.list'))

    category_name = category.name
    db.session.delete(category)
    db.session.commit()

    flash(f'La catégorie "{category_name}" a été supprimée.', 'success')
    return redirect(url_for('categories.list'))


@bp.route('/<int:category_id>/toggle', methods=['POST'])
@login_required
def toggle(category_id):
    """Activer/désactiver une catégorie personnalisée"""
    # Vérifier que l'utilisateur a le plan Premium
    if not current_user.can_create_custom_category():
        flash('La gestion des catégories personnalisées est réservée aux utilisateurs Premium.', 'warning')
        return redirect(url_for('main.pricing'))

    category = Category.query.get_or_404(category_id)

    # Vérifier que c'est bien une catégorie de l'utilisateur
    if category.user_id != current_user.id:
        flash('Vous ne pouvez modifier que vos propres catégories.', 'danger')
        return redirect(url_for('categories.list'))

    category.is_active = not category.is_active
    db.session.commit()

    status = 'activée' if category.is_active else 'désactivée'
    flash(f'La catégorie "{category.name}" a été {status}.', 'success')
    return redirect(url_for('categories.list'))


@bp.route('/<int:category_id>/customize', methods=['POST'])
@login_required
def customize(category_id):
    """Dupliquer une catégorie globale pour la personnaliser"""
    # Vérifier que l'utilisateur est Premium
    if not current_user.is_premium():
        flash('La personnalisation des catégories est réservée aux utilisateurs Premium.', 'warning')
        return redirect(url_for('main.pricing'))

    # Récupérer la catégorie globale
    global_category = Category.query.get_or_404(category_id)

    # Vérifier que c'est bien une catégorie globale
    if not global_category.is_global():
        flash('Seules les catégories par défaut peuvent être personnalisées.', 'danger')
        return redirect(url_for('categories.list'))

    # Vérifier si l'utilisateur a déjà une catégorie avec ce nom
    existing = current_user.custom_categories.filter_by(name=global_category.name).first()
    if existing:
        flash(f'Vous avez déjà une catégorie nommée "{global_category.name}". Modifiez-la directement.', 'warning')
        return redirect(url_for('categories.edit', category_id=existing.id))

    # Créer une copie personnalisée
    custom_category = Category(
        user_id=current_user.id,
        name=global_category.name,
        description=global_category.description,
        logo_data=global_category.logo_data,
        logo_mime_type=global_category.logo_mime_type,
        website_url=global_category.website_url,
        color=global_category.color,
        icon=global_category.icon,
        is_active=True
    )

    db.session.add(custom_category)
    db.session.commit()

    flash(f'La catégorie "{global_category.name}" a été dupliquée. Vous pouvez maintenant la personnaliser.', 'success')
    return redirect(url_for('categories.edit', category_id=custom_category.id))


@bp.route('/<int:category_id>/hide', methods=['POST'])
@login_required
def hide(category_id):
    """Masquer une catégorie globale"""
    # Vérifier que l'utilisateur est Premium
    if not current_user.is_premium():
        flash('Le masquage des catégories est réservé aux utilisateurs Premium.', 'warning')
        return redirect(url_for('main.pricing'))

    # Récupérer la catégorie
    category = Category.query.get_or_404(category_id)

    # Vérifier que c'est bien une catégorie globale
    if not category.is_global():
        flash('Seules les catégories par défaut peuvent être masquées.', 'danger')
        return redirect(url_for('categories.list'))

    # Ajouter à la liste des catégories masquées
    if category not in current_user.hidden_categories_list:
        current_user.hidden_categories_list.append(category)
        db.session.commit()
        flash(f'La catégorie "{category.name}" a été masquée.', 'success')
    else:
        flash(f'La catégorie "{category.name}" est déjà masquée.', 'info')

    return redirect(url_for('categories.list'))


@bp.route('/<int:category_id>/unhide', methods=['POST'])
@login_required
def unhide(category_id):
    """Afficher une catégorie globale masquée"""
    # Vérifier que l'utilisateur est Premium
    if not current_user.is_premium():
        flash('La gestion des catégories masquées est réservée aux utilisateurs Premium.', 'warning')
        return redirect(url_for('main.pricing'))

    # Récupérer la catégorie
    category = Category.query.get_or_404(category_id)

    # Retirer de la liste des catégories masquées
    if category in current_user.hidden_categories_list:
        current_user.hidden_categories_list.remove(category)
        db.session.commit()
        flash(f'La catégorie "{category.name}" est de nouveau visible.', 'success')
    else:
        flash(f'La catégorie "{category.name}" n\'était pas masquée.', 'info')

    return redirect(url_for('categories.list'))
