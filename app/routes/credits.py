from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Credit, Category, CreditType
from datetime import datetime, timedelta

bp = Blueprint('credits', __name__, url_prefix='/credits')


def get_user_categories():
    """Récupère les catégories globales et personnalisées de l'utilisateur actuel"""
    # Catégories globales (par défaut)
    global_categories = Category.query.filter_by(user_id=None, is_active=True).order_by(Category.name).all()

    # Catégories personnalisées de l'utilisateur
    custom_categories = current_user.custom_categories.filter_by(is_active=True).order_by(Category.name).all()

    # Combiner les deux listes
    return global_categories + custom_categories


def get_user_credit_types():
    """Récupère les types de crédits globaux et personnalisés de l'utilisateur actuel"""
    # Types globaux (par défaut)
    global_types = CreditType.query.filter_by(user_id=None, is_active=True).order_by(CreditType.name).all()

    # Types personnalisés de l'utilisateur
    custom_types = current_user.custom_credit_types.filter_by(is_active=True).order_by(CreditType.name).all()

    # Combiner les deux listes
    return global_types + custom_types


@bp.route('/')
@login_required
def list():
    page = request.args.get('page', 1, type=int)
    filter_status = request.args.get('status', 'all')
    filter_category = request.args.get('category', None, type=int)
    filter_type_id = request.args.get('type', None, type=int)

    query = current_user.credits

    if filter_status == 'active':
        query = query.filter_by(is_active=True)
    elif filter_status == 'inactive':
        query = query.filter_by(is_active=False)

    if filter_category:
        query = query.filter_by(category_id=filter_category)

    if filter_type_id:
        query = query.filter_by(credit_type_id=filter_type_id)

    credits = query.order_by(Credit.next_payment_date).paginate(
        page=page, per_page=10, error_out=False
    )

    categories = get_user_categories()
    credit_types = get_user_credit_types()

    return render_template('credits/list.html',
                         credits=credits,
                         categories=categories,
                         credit_types=credit_types,
                         filter_status=filter_status,
                         filter_category=filter_category,
                         filter_type_id=filter_type_id)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        amount = float(request.form.get('amount'))
        currency = request.form.get('currency', 'EUR')
        credit_type_id = request.form.get('credit_type_id', type=int)
        billing_cycle = request.form.get('billing_cycle')
        category_id = request.form.get('category_id', type=int)
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        total_amount = request.form.get('total_amount', type=float)
        remaining_amount = request.form.get('remaining_amount', type=float)
        interest_rate = request.form.get('interest_rate', type=float)

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

        credit = Credit(
            user_id=current_user.id,
            name=name,
            description=description,
            amount=amount,
            currency=currency,
            credit_type_id=credit_type_id if credit_type_id else None,
            billing_cycle=billing_cycle,
            category_id=category_id if category_id else None,
            start_date=start_date,
            end_date=end_date,
            next_payment_date=start_date,
            total_amount=total_amount,
            remaining_amount=remaining_amount,
            interest_rate=interest_rate
        )

        # Calculer la prochaine date de paiement
        if billing_cycle == 'monthly':
            credit.next_payment_date = start_date + timedelta(days=30)
        elif billing_cycle == 'quarterly':
            credit.next_payment_date = start_date + timedelta(days=90)
        elif billing_cycle == 'yearly':
            credit.next_payment_date = start_date + timedelta(days=365)

        db.session.add(credit)
        db.session.commit()

        flash(f'Le crédit "{name}" a été ajouté avec succès !', 'success')
        return redirect(url_for('credits.list'))

    categories = get_user_categories()
    credit_types = get_user_credit_types()
    return render_template('credits/add.html', categories=categories, credit_types=credit_types)


@bp.route('/<int:credit_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(credit_id):
    credit = Credit.query.get_or_404(credit_id)

    if credit.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce crédit.', 'danger')
        return redirect(url_for('credits.list'))

    if request.method == 'POST':
        credit.name = request.form.get('name')
        credit.description = request.form.get('description')
        credit.amount = float(request.form.get('amount'))
        credit.currency = request.form.get('currency', 'EUR')
        credit.credit_type_id = request.form.get('credit_type_id', type=int) or None
        credit.billing_cycle = request.form.get('billing_cycle')
        credit.category_id = request.form.get('category_id', type=int) or None

        end_date_str = request.form.get('end_date')
        credit.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

        credit.total_amount = request.form.get('total_amount', type=float)
        credit.remaining_amount = request.form.get('remaining_amount', type=float)
        credit.interest_rate = request.form.get('interest_rate', type=float)

        db.session.commit()

        flash(f'Le crédit "{credit.name}" a été mis à jour.', 'success')
        return redirect(url_for('credits.list'))

    categories = get_user_categories()
    credit_types = get_user_credit_types()
    return render_template('credits/edit.html',
                         credit=credit,
                         categories=categories,
                         credit_types=credit_types)


@bp.route('/<int:credit_id>/delete', methods=['POST'])
@login_required
def delete(credit_id):
    credit = Credit.query.get_or_404(credit_id)

    if credit.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce crédit.', 'danger')
        return redirect(url_for('credits.list'))

    credit_name = credit.name
    db.session.delete(credit)
    db.session.commit()

    flash(f'Le crédit "{credit_name}" a été supprimé.', 'success')
    return redirect(url_for('credits.list'))


@bp.route('/<int:credit_id>/toggle', methods=['POST'])
@login_required
def toggle(credit_id):
    credit = Credit.query.get_or_404(credit_id)

    if credit.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce crédit.', 'danger')
        return redirect(url_for('credits.list'))

    credit.is_active = not credit.is_active
    if not credit.is_active:
        credit.closed_at = datetime.utcnow()
    else:
        credit.closed_at = None

    db.session.commit()

    status = 'activé' if credit.is_active else 'clôturé'
    flash(f'Le crédit "{credit.name}" a été {status}.', 'success')
    return redirect(url_for('credits.list'))


@bp.route('/<int:credit_id>')
@login_required
def detail(credit_id):
    credit = Credit.query.get_or_404(credit_id)

    if credit.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce crédit.', 'danger')
        return redirect(url_for('credits.list'))

    return render_template('credits/detail.html', credit=credit)
