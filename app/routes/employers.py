from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, Response
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app import db, limiter
from app.models import Employer, EmployerDocument
from app.utils.file_security import validate_upload, get_safe_content_disposition
from datetime import datetime
import base64
import io

bp = Blueprint('employers', __name__, url_prefix='/employers')

def get_contract_types():
    """Retourne les types de contrats avec traduction"""
    return [
        ('cdi', _('CDI')),
        ('cdd', _('CDD')),
        ('interim', _('Intérim')),
        ('freelance', _('Freelance')),
        ('stage', _('Stage')),
        ('apprentissage', _('Apprentissage')),
        ('other', _('Autre')),
    ]

def get_document_types():
    """Retourne les types de documents avec traduction"""
    return [
        ('contract', _('Contrat de travail'), 'fa-file-signature', '#6366f1'),
        ('payslip', _('Fiche de paie'), 'fa-file-invoice-dollar', '#10b981'),
        ('expense_report', _('Fiche de frais'), 'fa-receipt', '#ec4899'),
        ('certificate', _('Attestation'), 'fa-certificate', '#f59e0b'),
        ('amendment', _('Avenant'), 'fa-file-contract', '#8b5cf6'),
        ('other', _('Autre document'), 'fa-file', '#6c757d'),
    ]

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


@bp.route('/', endpoint='list')
@login_required
def employer_list():
    page = request.args.get('page', 1, type=int)
    filter_status = request.args.get('status', 'all')

    query = current_user.employers

    if filter_status == 'active':
        query = query.filter_by(is_active=True)
    elif filter_status == 'inactive':
        query = query.filter_by(is_active=False)

    employers = query.order_by(Employer.name).paginate(
        page=page, per_page=10, error_out=False
    )

    return render_template('employers/list.html',
                         employers=employers,
                         filter_status=filter_status)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        postal_code = request.form.get('postal_code')
        city = request.form.get('city')
        country = request.form.get('country')
        phone = request.form.get('phone')
        email = request.form.get('email')
        website = request.form.get('website')
        siret = request.form.get('siret')
        job_title = request.form.get('job_title')
        contract_type = request.form.get('contract_type')
        hire_date_str = request.form.get('hire_date')
        end_date_str = request.form.get('end_date')
        notes = request.form.get('notes')

        hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d').date() if hire_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

        employer = Employer(
            user_id=current_user.id,
            name=name,
            address=address,
            postal_code=postal_code,
            city=city,
            country=country,
            phone=phone,
            email=email,
            website=website,
            siret=siret,
            job_title=job_title,
            contract_type=contract_type if contract_type else None,
            hire_date=hire_date,
            end_date=end_date,
            notes=notes,
            is_active=end_date is None
        )

        # Gestion du logo
        if 'logo' in request.files:
            logo_file = request.files['logo']
            if logo_file and logo_file.filename:
                logo_data = base64.b64encode(logo_file.read()).decode('utf-8')
                employer.logo_data = logo_data
                employer.logo_mime_type = logo_file.content_type

        db.session.add(employer)
        db.session.commit()

        flash(_('L\'employeur "%(name)s" a été ajouté avec succès !', name=name), 'success')
        return redirect(url_for('employers.detail', employer_id=employer.id))

    return render_template('employers/add.html', contract_types=get_contract_types())


@bp.route('/<int:employer_id>')
@login_required
def detail(employer_id):
    employer = Employer.query.get_or_404(employer_id)

    if employer.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à cet employeur.'), 'danger')
        return redirect(url_for('employers.list'))

    # Récupérer les documents groupés par type et année
    filter_type = request.args.get('doc_type', None)
    filter_year = request.args.get('year', None, type=int)
    search = request.args.get('search', None)

    query = employer.documents

    if filter_type:
        query = query.filter_by(document_type=filter_type)
    if filter_year:
        query = query.filter_by(year=filter_year)
    if search:
        query = query.filter(EmployerDocument.name.ilike(f'%{search}%'))

    documents = query.order_by(EmployerDocument.year.desc(), EmployerDocument.month.desc(), EmployerDocument.document_date.desc()).all()

    # Obtenir les années disponibles pour le filtre
    years = db.session.query(EmployerDocument.year).filter(
        EmployerDocument.employer_id == employer_id,
        EmployerDocument.year.isnot(None)
    ).distinct().order_by(EmployerDocument.year.desc()).all()
    years = [y[0] for y in years]

    # Compter les documents par type
    doc_counts = {}
    for doc_type, _, _, _ in get_document_types():
        doc_counts[doc_type] = employer.documents.filter_by(document_type=doc_type).count()

    # Calculer la taille totale des documents
    total_size = db.session.query(db.func.sum(EmployerDocument.file_size)).filter(
        EmployerDocument.employer_id == employer_id
    ).scalar() or 0

    return render_template('employers/detail.html',
                         employer=employer,
                         documents=documents,
                         document_types=get_document_types(),
                         years=years,
                         filter_type=filter_type,
                         filter_year=filter_year,
                         search=search,
                         doc_counts=doc_counts,
                         total_size=total_size,
                         get_document_type_info=get_document_type_info)


@bp.route('/<int:employer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(employer_id):
    employer = Employer.query.get_or_404(employer_id)

    if employer.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à cet employeur.'), 'danger')
        return redirect(url_for('employers.list'))

    if request.method == 'POST':
        employer.name = request.form.get('name')
        employer.address = request.form.get('address')
        employer.postal_code = request.form.get('postal_code')
        employer.city = request.form.get('city')
        employer.country = request.form.get('country')
        employer.phone = request.form.get('phone')
        employer.email = request.form.get('email')
        employer.website = request.form.get('website')
        employer.siret = request.form.get('siret')
        employer.job_title = request.form.get('job_title')
        employer.contract_type = request.form.get('contract_type') or None
        employer.notes = request.form.get('notes')

        hire_date_str = request.form.get('hire_date')
        end_date_str = request.form.get('end_date')
        employer.hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d').date() if hire_date_str else None
        employer.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        employer.is_active = employer.end_date is None

        # Gestion du logo
        if 'logo' in request.files:
            logo_file = request.files['logo']
            if logo_file and logo_file.filename:
                logo_data = base64.b64encode(logo_file.read()).decode('utf-8')
                employer.logo_data = logo_data
                employer.logo_mime_type = logo_file.content_type

        # Supprimer le logo si demandé
        if request.form.get('remove_logo') == '1':
            employer.logo_data = None
            employer.logo_mime_type = None

        db.session.commit()

        flash(_('L\'employeur "%(name)s" a été mis à jour.', name=employer.name), 'success')
        return redirect(url_for('employers.detail', employer_id=employer.id))

    return render_template('employers/edit.html',
                         employer=employer,
                         contract_types=get_contract_types())


@bp.route('/<int:employer_id>/delete', methods=['POST'])
@login_required
def delete(employer_id):
    employer = Employer.query.get_or_404(employer_id)

    if employer.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à cet employeur.'), 'danger')
        return redirect(url_for('employers.list'))

    employer_name = employer.name
    db.session.delete(employer)
    db.session.commit()

    flash(_('L\'employeur "%(name)s" a été supprimé.', name=employer_name), 'success')
    return redirect(url_for('employers.list'))


# Routes pour les documents
@bp.route('/<int:employer_id>/documents/add', methods=['GET', 'POST'])
@login_required
@limiter.limit("100 per hour")
def add_document(employer_id):
    employer = Employer.query.get_or_404(employer_id)

    if employer.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à cet employeur.'), 'danger')
        return redirect(url_for('employers.list'))

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

        document = EmployerDocument(
            user_id=current_user.id,
            employer_id=employer_id,
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
                    flash(_(error), 'danger')
                    return redirect(url_for('employers.add_document', employer_id=employer_id))

                document.file_data = file_data
                document.file_name = safe_filename
                document.file_mime_type = file.content_type
                document.file_size = len(file_data)

        db.session.add(document)
        db.session.commit()

        flash(_('Le document "%(name)s" a été ajouté avec succès !', name=name), 'success')
        return redirect(url_for('employers.detail', employer_id=employer_id))

    current_year = datetime.now().year
    years = list(range(current_year, current_year - 20, -1))

    return render_template('employers/add_document.html',
                         employer=employer,
                         document_types=get_document_types(),
                         months=get_months(),
                         years=years)


@bp.route('/documents/<int:document_id>/download')
@login_required
def download_document(document_id):
    document = EmployerDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce document.'), 'danger')
        return redirect(url_for('employers.list'))

    if not document.file_data:
        flash(_('Ce document n\'a pas de fichier attaché.'), 'warning')
        return redirect(url_for('employers.detail', employer_id=document.employer_id))

    return Response(
        document.file_data,
        mimetype=document.file_mime_type or 'application/octet-stream',
        headers={'Content-Disposition': get_safe_content_disposition(document.file_name, inline=False)}
    )


@bp.route('/documents/<int:document_id>/view')
@login_required
def view_document(document_id):
    document = EmployerDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce document.'), 'danger')
        return redirect(url_for('employers.list'))

    if not document.file_data:
        flash(_('Ce document n\'a pas de fichier attaché.'), 'warning')
        return redirect(url_for('employers.detail', employer_id=document.employer_id))

    return Response(
        document.file_data,
        mimetype=document.file_mime_type or 'application/octet-stream',
        headers={'Content-Disposition': get_safe_content_disposition(document.file_name, inline=True)}
    )


@bp.route('/documents/<int:document_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_document(document_id):
    document = EmployerDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce document.'), 'danger')
        return redirect(url_for('employers.list'))

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
                    flash(_(error), 'danger')
                    return redirect(url_for('employers.edit_document', document_id=document_id))

                document.file_data = file_data
                document.file_name = safe_filename
                document.file_mime_type = file.content_type
                document.file_size = len(file_data)

        db.session.commit()

        flash(_('Le document "%(name)s" a été mis à jour.', name=document.name), 'success')
        return redirect(url_for('employers.detail', employer_id=document.employer_id))

    current_year = datetime.now().year
    years = list(range(current_year, current_year - 20, -1))

    return render_template('employers/edit_document.html',
                         document=document,
                         employer=document.employer,
                         document_types=get_document_types(),
                         months=get_months(),
                         years=years)


@bp.route('/documents/<int:document_id>/delete', methods=['POST'])
@login_required
def delete_document(document_id):
    document = EmployerDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash(_('Vous n\'avez pas accès à ce document.'), 'danger')
        return redirect(url_for('employers.list'))

    employer_id = document.employer_id
    document_name = document.name
    db.session.delete(document)
    db.session.commit()

    flash(_('Le document "%(name)s" a été supprimé.', name=document_name), 'success')
    return redirect(url_for('employers.detail', employer_id=employer_id))
