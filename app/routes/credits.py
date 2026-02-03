from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app import db, limiter
from app.models import Credit, Category, CreditType, CreditDocument, Bank, Notification
from app.utils.transactions import generate_future_transactions, update_future_transactions, cancel_future_transactions, calculate_next_future_date, delete_all_transactions
from app.utils.file_security import validate_upload, get_safe_content_disposition
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

bp = Blueprint('credits', __name__, url_prefix='/credits')

# Types de documents disponibles pour les crédits
def get_document_types():
    """Retourne les types de documents avec traduction"""
    return [
        ('contract', _('Contrat de crédit'), 'fa-file-signature', '#6366f1'),
        ('statement', _('Relevé'), 'fa-file-invoice', '#10b981'),
        ('insurance', _('Assurance'), 'fa-shield-alt', '#f59e0b'),
        ('amendment', _('Avenant'), 'fa-file-contract', '#8b5cf6'),
        ('correspondence', _('Courrier'), 'fa-envelope', '#06b6d4'),
        ('other', _('Autre document'), 'fa-file', '#6c757d'),
    ]

# Mois
def get_months():
    """Retourne les mois avec traduction"""
    return [
        (1, _('Janvier')), (2, _('Février')), (3, _('Mars')), (4, _('Avril')),
        (5, _('Mai')), (6, _('Juin')), (7, _('Juillet')), (8, _('Août')),
        (9, _('Septembre')), (10, _('Octobre')), (11, _('Novembre')), (12, _('Décembre'))
    ]


def get_document_type_info(type_code):
    """Retourne les informations d'un type de document"""
    for code, name, icon, color in get_document_types():
        if code == type_code:
            return {'code': code, 'name': name, 'icon': icon, 'color': color}
    return {'code': 'other', 'name': _('Autre'), 'icon': 'fa-file', 'color': '#6c757d'}


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
def list_credits():
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
        # Vérifier si l'utilisateur peut ajouter un crédit
        if not current_user.can_add_credit():
            flash(_('Vous avez atteint la limite de crédits pour le plan gratuit. Passez au plan Premium pour ajouter des crédits illimités.'), 'warning')
            return redirect(url_for('credits.list_credits'))

        name = request.form.get('name')
        description = request.form.get('description')
        amount = float(request.form.get('amount'))
        currency = request.form.get('currency', 'EUR')
        credit_type_id = request.form.get('credit_type_id', type=int)
        bank_id = request.form.get('bank_id', type=int)
        billing_cycle = request.form.get('billing_cycle')
        category_id = request.form.get('category_id', type=int)
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        total_amount = request.form.get('total_amount', type=float)
        remaining_amount = request.form.get('remaining_amount', type=float)
        interest_rate = request.form.get('interest_rate', type=float)

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

        # Calculer la prochaine date de paiement future
        next_payment_date = calculate_next_future_date(start_date, billing_cycle)

        credit = Credit(
            user_id=current_user.id,
            name=name,
            description=description,
            amount=amount,
            currency=currency,
            credit_type_id=credit_type_id if credit_type_id else None,
            bank_id=bank_id if bank_id else None,
            billing_cycle=billing_cycle,
            category_id=category_id if category_id else None,
            start_date=start_date,
            end_date=end_date,
            next_payment_date=next_payment_date,
            total_amount=total_amount,
            remaining_amount=remaining_amount,
            interest_rate=interest_rate
        )

        db.session.add(credit)
        db.session.commit()

        # Générer les transactions futures (12 mois)
        generate_future_transactions(credit, 'credit', 12)
        db.session.commit()

        # Créer une notification
        notification = Notification(
            user_id=current_user.id,
            credit_id=credit.id,
            created_by_user_id=current_user.id,
            type='credit_added',
            title=_('Nouveau crédit ajouté'),
            message=_('Votre crédit "%(name)s" a été ajouté avec succès.', name=name)
        )
        db.session.add(notification)
        db.session.commit()

        # Envoyer un email de notification si activé
        from app.utils.email import send_notification_email
        send_notification_email(current_user, notification)

        flash(_('Le crédit "%(name)s" a été ajouté avec succès !', name=name), 'success')
        return redirect(url_for('credits.list_credits'))

    from app.models import Bank
    categories = get_user_categories()
    credit_types = get_user_credit_types()
    banks = Bank.query.filter_by(user_id=current_user.id, is_active=True).order_by(Bank.name).all()
    return render_template('credits/add.html', categories=categories, credit_types=credit_types, banks=banks)


@bp.route('/<int:credit_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(credit_id):
    credit = Credit.query.get_or_404(credit_id)

    if credit.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce crédit.'), 'danger')
        return redirect(url_for('credits.list_credits'))

    if request.method == 'POST':
        credit.name = request.form.get('name')
        credit.description = request.form.get('description')
        credit.amount = float(request.form.get('amount'))
        credit.currency = request.form.get('currency', 'EUR')
        credit.credit_type_id = request.form.get('credit_type_id', type=int) or None
        credit.bank_id = request.form.get('bank_id', type=int) or None
        credit.billing_cycle = request.form.get('billing_cycle')
        credit.category_id = request.form.get('category_id', type=int) or None

        end_date_str = request.form.get('end_date')
        credit.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

        credit.total_amount = request.form.get('total_amount', type=float)
        credit.remaining_amount = request.form.get('remaining_amount', type=float)
        credit.interest_rate = request.form.get('interest_rate', type=float)

        # Recalculer la prochaine date de paiement future basée sur la start_date et le nouveau billing_cycle
        credit.next_payment_date = calculate_next_future_date(credit.start_date, credit.billing_cycle)

        db.session.commit()

        # Mettre à jour les transactions futures
        update_future_transactions(credit, 'credit')
        db.session.commit()

        flash(_('Le crédit "%(name)s" a été mis à jour.', name=credit.name), 'success')
        return redirect(url_for('credits.list_credits'))

    from app.models import Bank
    categories = get_user_categories()
    credit_types = get_user_credit_types()
    banks = Bank.query.filter_by(user_id=current_user.id, is_active=True).order_by(Bank.name).all()
    return render_template('credits/edit.html',
                         credit=credit,
                         categories=categories,
                         credit_types=credit_types,
                         banks=banks)


@bp.route('/<int:credit_id>/delete', methods=['POST'])
@login_required
def delete(credit_id):
    credit = Credit.query.get_or_404(credit_id)

    if credit.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce crédit.'), 'danger')
        return redirect(url_for('credits.list_credits'))

    credit_name = credit.name

    # Supprimer toutes les transactions associées
    delete_all_transactions(credit.id, 'credit')

    db.session.delete(credit)
    db.session.commit()

    flash(_('Le crédit "%(name)s" et toutes ses transactions ont été supprimés.', name=credit_name), 'success')

    # Rediriger vers la page balance si le paramètre est présent
    redirect_to = request.args.get('redirect_to', 'credits.list_credits')
    if redirect_to == 'balance':
        return redirect(url_for('main.balance'))
    return redirect(url_for('credits.list_credits'))


@bp.route('/<int:credit_id>/toggle', methods=['POST'])
@login_required
def toggle(credit_id):
    credit = Credit.query.get_or_404(credit_id)

    if credit.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce crédit.'), 'danger')
        return redirect(url_for('credits.list_credits'))

    credit.is_active = not credit.is_active
    if not credit.is_active:
        credit.closed_at = datetime.utcnow()
        # Annuler les transactions futures
        cancel_future_transactions(credit.id, 'credit')
    else:
        credit.closed_at = None
        # Régénérer les transactions futures
        generate_future_transactions(credit, 'credit', 12)

    db.session.commit()

    status = _('activé') if credit.is_active else _('clôturé')
    flash(_('Le crédit "%(name)s" a été %(status)s.', name=credit.name, status=status), 'success')
    return redirect(url_for('credits.list_credits'))


@bp.route('/<int:credit_id>')
@login_required
def detail(credit_id):
    credit = Credit.query.get_or_404(credit_id)

    if credit.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce crédit.'), 'danger')
        return redirect(url_for('credits.list_credits'))

    # Récupérer les documents avec filtres
    filter_type = request.args.get('doc_type', None)
    filter_year = request.args.get('year', None, type=int)
    search = request.args.get('search', None)

    query = credit.documents

    if filter_type:
        query = query.filter_by(document_type=filter_type)
    if filter_year:
        query = query.filter_by(year=filter_year)
    if search:
        query = query.filter(CreditDocument.name.ilike(f'%{search}%'))

    documents = query.order_by(CreditDocument.year.desc(), CreditDocument.month.desc(), CreditDocument.document_date.desc()).all()

    # Obtenir les années disponibles pour le filtre
    years = db.session.query(CreditDocument.year).filter(
        CreditDocument.credit_id == credit_id,
        CreditDocument.year.isnot(None)
    ).distinct().order_by(CreditDocument.year.desc()).all()
    years = [y[0] for y in years]

    # Compter les documents par type
    doc_counts = {}
    for doc_type, _, _, _ in get_document_types():
        doc_counts[doc_type] = credit.documents.filter_by(document_type=doc_type).count()

    # Calculer la taille totale des documents
    total_size = db.session.query(db.func.sum(CreditDocument.file_size)).filter(
        CreditDocument.credit_id == credit_id
    ).scalar() or 0

    return render_template('credits/detail.html',
                         credit=credit,
                         documents=documents,
                         document_types=get_document_types(),
                         years=years,
                         filter_type=filter_type,
                         filter_year=filter_year,
                         search=search,
                         doc_counts=doc_counts,
                         total_size=total_size,
                         get_document_type_info=get_document_type_info)


@bp.route('/<int:credit_id>/documents/add', methods=['GET', 'POST'])
@login_required
@limiter.limit("100 per hour")
def add_document(credit_id):
    credit = Credit.query.get_or_404(credit_id)

    if credit.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce crédit.'), 'danger')
        return redirect(url_for('credits.list_credits'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        document_type = request.form.get('document_type')
        document_date_str = request.form.get('document_date')
        year_str = request.form.get('year')
        year = int(year_str) if year_str else None
        month_str = request.form.get('month')
        month = int(month_str) if month_str else None

        document_date = datetime.strptime(document_date_str, '%Y-%m-%d').date() if document_date_str else None

        # Auto-remplir année et mois depuis la date si non fournis
        if document_date and not year:
            year = document_date.year
        if document_date and not month:
            month = document_date.month

        document = CreditDocument(
            user_id=current_user.id,
            credit_id=credit_id,
            name=name,
            description=description,
            document_type=document_type,
            document_date=document_date,
            year=year,
            month=month
        )

        # Gestion du fichier avec validation de sécurité
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                success, error, file_data, safe_filename = validate_upload(file)
                if not success:
                    flash(error, 'danger')
                    return redirect(url_for('credits.add_document', credit_id=credit_id))

                document.file_data = file_data
                document.file_name = safe_filename
                document.file_mime_type = file.content_type
                document.file_size = len(file_data)

        db.session.add(document)
        db.session.commit()

        flash(_('Le document "%(name)s" a été ajouté avec succès !', name=name), 'success')
        return redirect(url_for('credits.detail', credit_id=credit_id))

    current_year = datetime.now().year
    years = list(range(current_year, current_year - 20, -1))

    return render_template('credits/add_document.html',
                         credit=credit,
                         document_types=get_document_types(),
                         months=get_months(),
                         years=years)


@bp.route('/documents/<int:document_id>/download')
@login_required
def download_document(document_id):
    document = CreditDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce document.'), 'danger')
        return redirect(url_for('credits.list_credits'))

    if not document.file_data:
        flash(_('Ce document n\'a pas de fichier attaché.'), 'warning')
        return redirect(url_for('credits.detail', credit_id=document.credit_id))

    return Response(
        document.file_data,
        mimetype=document.file_mime_type or 'application/octet-stream',
        headers={'Content-Disposition': get_safe_content_disposition(document.file_name, inline=False)}
    )


@bp.route('/documents/<int:document_id>/view')
@login_required
def view_document(document_id):
    document = CreditDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce document.'), 'danger')
        return redirect(url_for('credits.list_credits'))

    if not document.file_data:
        flash(_('Ce document n\'a pas de fichier attaché.'), 'warning')
        return redirect(url_for('credits.detail', credit_id=document.credit_id))

    return Response(
        document.file_data,
        mimetype=document.file_mime_type or 'application/octet-stream',
        headers={'Content-Disposition': get_safe_content_disposition(document.file_name, inline=True)}
    )


@bp.route('/documents/<int:document_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_document(document_id):
    document = CreditDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce document.'), 'danger')
        return redirect(url_for('credits.list_credits'))

    if request.method == 'POST':
        document.name = request.form.get('name')
        document.description = request.form.get('description')
        document.document_type = request.form.get('document_type')
        document.year = request.form.get('year', type=int)
        document.month = request.form.get('month', type=int)

        document_date_str = request.form.get('document_date')
        document.document_date = datetime.strptime(document_date_str, '%Y-%m-%d').date() if document_date_str else None

        # Gestion du fichier avec validation de sécurité
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                success, error, file_data, safe_filename = validate_upload(file)
                if not success:
                    flash(error, 'danger')
                    return redirect(url_for('credits.edit_document', document_id=document_id))

                document.file_data = file_data
                document.file_name = safe_filename
                document.file_mime_type = file.content_type
                document.file_size = len(file_data)

        db.session.commit()

        flash(_('Le document "%(name)s" a été mis à jour.', name=document.name), 'success')
        return redirect(url_for('credits.detail', credit_id=document.credit_id))

    current_year = datetime.now().year
    years = list(range(current_year, current_year - 20, -1))

    return render_template('credits/edit_document.html',
                         document=document,
                         credit=document.credit,
                         document_types=get_document_types(),
                         months=get_months(),
                         years=years)


@bp.route('/documents/<int:document_id>/delete', methods=['POST'])
@login_required
def delete_document(document_id):
    document = CreditDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce document.'), 'danger')
        return redirect(url_for('credits.list_credits'))

    credit_id = document.credit_id
    document_name = document.name
    db.session.delete(document)
    db.session.commit()

    flash(_('Le document "%(name)s" a été supprimé.', name=document_name), 'success')
    return redirect(url_for('credits.detail', credit_id=credit_id))
