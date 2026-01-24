from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Provider

bp = Blueprint('providers', __name__, url_prefix='/providers')


@bp.route('/', endpoint='list')
@login_required
def provider_list():
    page = request.args.get('page', 1, type=int)
    filter_status = request.args.get('status', 'all')

    query = current_user.providers

    if filter_status == 'active':
        query = query.filter_by(is_active=True)
    elif filter_status == 'inactive':
        query = query.filter_by(is_active=False)

    providers = query.order_by(Provider.name).paginate(
        page=page, per_page=10, error_out=False
    )

    return render_template('providers/list.html',
                         providers=providers,
                         filter_status=filter_status)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form.get('name')
        provider_type = request.form.get('provider_type')
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address')
        notes = request.form.get('notes')

        provider = Provider(
            user_id=current_user.id,
            name=name,
            provider_type=provider_type,
            phone=phone,
            email=email,
            address=address,
            notes=notes
        )

        db.session.add(provider)
        db.session.commit()

        flash(f'Le prestataire "{name}" a été ajouté avec succès !', 'success')
        return redirect(url_for('providers.list'))

    return render_template('providers/add.html')


@bp.route('/<int:provider_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(provider_id):
    provider = Provider.query.get_or_404(provider_id)

    if provider.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce prestataire.', 'danger')
        return redirect(url_for('providers.list'))

    if request.method == 'POST':
        provider.name = request.form.get('name')
        provider.provider_type = request.form.get('provider_type')
        provider.phone = request.form.get('phone')
        provider.email = request.form.get('email')
        provider.address = request.form.get('address')
        provider.notes = request.form.get('notes')

        db.session.commit()

        flash(f'Le prestataire "{provider.name}" a été modifié avec succès !', 'success')
        return redirect(url_for('providers.list'))

    return render_template('providers/edit.html', provider=provider)


@bp.route('/<int:provider_id>/delete', methods=['POST'])
@login_required
def delete(provider_id):
    provider = Provider.query.get_or_404(provider_id)

    if provider.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce prestataire.', 'danger')
        return redirect(url_for('providers.list'))

    # Vérifier s'il y a des rappels associés
    if provider.reminders.count() > 0:
        flash('Impossible de supprimer ce prestataire car des rappels y sont associés.', 'danger')
        return redirect(url_for('providers.list'))

    name = provider.name
    db.session.delete(provider)
    db.session.commit()

    flash(f'Le prestataire "{name}" a été supprimé.', 'success')
    return redirect(url_for('providers.list'))
