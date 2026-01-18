from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Revenue, Employer, Notification
from app.utils.transactions import generate_future_transactions, update_future_transactions, cancel_future_transactions, calculate_next_future_date, delete_all_transactions
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

bp = Blueprint('revenues', __name__, url_prefix='/revenues')


def get_user_employers():
    """Récupère les employeurs de l'utilisateur actuel"""
    return current_user.employers.filter_by(is_active=True).order_by(Employer.name).all()

# Types de revenus disponibles
REVENUE_TYPES = [
    ('salary', 'Salaire', 'fa-briefcase', '#10b981'),
    ('freelance', 'Freelance', 'fa-laptop', '#6366f1'),
    ('rental', 'Revenus locatifs', 'fa-home', '#f59e0b'),
    ('investment', 'Investissements', 'fa-chart-line', '#8b5cf6'),
    ('pension', 'Pension/Retraite', 'fa-user-clock', '#3b82f6'),
    ('other', 'Autre', 'fa-coins', '#6c757d'),
]


def get_revenue_type_info(type_code):
    """Retourne les informations d'un type de revenu"""
    for code, name, icon, color in REVENUE_TYPES:
        if code == type_code:
            return {'code': code, 'name': name, 'icon': icon, 'color': color}
    return {'code': 'other', 'name': 'Autre', 'icon': 'fa-coins', 'color': '#6c757d'}


@bp.route('/')
@login_required
def list():
    page = request.args.get('page', 1, type=int)
    filter_status = request.args.get('status', 'all')
    filter_type = request.args.get('type', None)

    query = current_user.revenues

    if filter_status == 'active':
        query = query.filter_by(is_active=True)
    elif filter_status == 'inactive':
        query = query.filter_by(is_active=False)

    if filter_type:
        query = query.filter_by(revenue_type=filter_type)

    revenues = query.order_by(Revenue.next_payment_date).paginate(
        page=page, per_page=10, error_out=False
    )

    employers = get_user_employers()
    return render_template('revenues/list.html',
                         revenues=revenues,
                         revenue_types=REVENUE_TYPES,
                         employers=employers,
                         filter_status=filter_status,
                         filter_type=filter_type,
                         get_revenue_type_info=get_revenue_type_info)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        # Vérifier si l'utilisateur peut ajouter un revenu
        if not current_user.can_add_revenue():
            flash('Vous avez atteint la limite de revenus pour le plan gratuit. Passez au plan Premium pour ajouter des revenus illimités.', 'warning')
            return redirect(url_for('revenues.list'))

        name = request.form.get('name')
        description = request.form.get('description')
        employer_id = request.form.get('employer_id', type=int)
        amount = float(request.form.get('amount'))
        currency = request.form.get('currency', 'EUR')
        revenue_type = request.form.get('revenue_type')
        billing_cycle = request.form.get('billing_cycle')
        start_date_str = request.form.get('start_date')

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

        # Calculer la prochaine date de paiement future
        next_payment_date = calculate_next_future_date(start_date, billing_cycle)

        revenue = Revenue(
            user_id=current_user.id,
            name=name,
            description=description,
            employer_id=employer_id if employer_id else None,
            amount=amount,
            currency=currency,
            revenue_type=revenue_type if revenue_type else None,
            billing_cycle=billing_cycle,
            start_date=start_date,
            next_payment_date=next_payment_date
        )

        db.session.add(revenue)
        db.session.commit()

        # Générer les transactions futures (12 mois)
        generate_future_transactions(revenue, 'revenue', 12)
        db.session.commit()

        # Créer une notification
        notification = Notification(
            user_id=current_user.id,
            revenue_id=revenue.id,
            created_by_user_id=current_user.id,
            type='revenue_added',
            title='Nouveau revenu ajouté',
            message=f'Votre revenu "{name}" a été ajouté avec succès.'
        )
        db.session.add(notification)
        db.session.commit()

        # Envoyer un email de notification si activé
        from app.utils.email import send_notification_email
        send_notification_email(current_user, notification)

        flash(f'Le revenu "{name}" a été ajouté avec succès !', 'success')
        return redirect(url_for('revenues.list'))

    employers = get_user_employers()
    return render_template('revenues/add.html', revenue_types=REVENUE_TYPES, employers=employers)


@bp.route('/<int:revenue_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(revenue_id):
    revenue = Revenue.query.get_or_404(revenue_id)

    if revenue.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce revenu.', 'danger')
        return redirect(url_for('revenues.list'))

    if request.method == 'POST':
        revenue.name = request.form.get('name')
        revenue.description = request.form.get('description')
        revenue.employer_id = request.form.get('employer_id', type=int) or None
        revenue.amount = float(request.form.get('amount'))
        revenue.currency = request.form.get('currency', 'EUR')
        revenue.revenue_type = request.form.get('revenue_type') or None
        revenue.billing_cycle = request.form.get('billing_cycle')

        # Recalculer la prochaine date de paiement future basée sur la start_date et le nouveau billing_cycle
        revenue.next_payment_date = calculate_next_future_date(revenue.start_date, revenue.billing_cycle)

        db.session.commit()

        # Mettre à jour les transactions futures
        update_future_transactions(revenue, 'revenue')
        db.session.commit()

        flash(f'Le revenu "{revenue.name}" a été mis à jour.', 'success')
        return redirect(url_for('revenues.list'))

    employers = get_user_employers()
    return render_template('revenues/edit.html',
                         revenue=revenue,
                         revenue_types=REVENUE_TYPES,
                         employers=employers)


@bp.route('/<int:revenue_id>/delete', methods=['POST'])
@login_required
def delete(revenue_id):
    revenue = Revenue.query.get_or_404(revenue_id)

    if revenue.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce revenu.', 'danger')
        return redirect(url_for('revenues.list'))

    revenue_name = revenue.name

    # Supprimer toutes les transactions associées
    delete_all_transactions(revenue.id, 'revenue')

    db.session.delete(revenue)
    db.session.commit()

    flash(f'Le revenu "{revenue_name}" et toutes ses transactions ont été supprimés.', 'success')

    # Rediriger vers la page balance si le paramètre est présent
    redirect_to = request.args.get('redirect_to', 'revenues.list')
    if redirect_to == 'balance':
        return redirect(url_for('main.balance'))
    return redirect(url_for('revenues.list'))


@bp.route('/<int:revenue_id>/toggle', methods=['POST'])
@login_required
def toggle(revenue_id):
    revenue = Revenue.query.get_or_404(revenue_id)

    if revenue.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce revenu.', 'danger')
        return redirect(url_for('revenues.list'))

    revenue.is_active = not revenue.is_active

    # Si désactivation, annuler les transactions futures
    if not revenue.is_active:
        cancel_future_transactions(revenue.id, 'revenue')
    # Si activation, régénérer les transactions futures
    else:
        generate_future_transactions(revenue, 'revenue', 12)

    db.session.commit()

    status = 'activé' if revenue.is_active else 'désactivé'
    flash(f'Le revenu "{revenue.name}" a été {status}.', 'success')
    return redirect(url_for('revenues.list'))


@bp.route('/<int:revenue_id>')
@login_required
def detail(revenue_id):
    revenue = Revenue.query.get_or_404(revenue_id)

    if revenue.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce revenu.', 'danger')
        return redirect(url_for('revenues.list'))

    return render_template('revenues/detail.html',
                         revenue=revenue,
                         get_revenue_type_info=get_revenue_type_info)
