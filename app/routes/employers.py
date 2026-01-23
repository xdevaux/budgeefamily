from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, Response
from flask_login import login_required, current_user
from app import db
from app.models import Employer, EmployerDocument
from datetime import datetime
import base64
import io

bp = Blueprint('employers', __name__, url_prefix='/employers')

# Types de contrats disponibles
CONTRACT_TYPES = [
    ('cdi', 'CDI'),
    ('cdd', 'CDD'),
    ('interim', 'Intérim'),
    ('freelance', 'Freelance'),
    ('stage', 'Stage'),
    ('apprentissage', 'Apprentissage'),
    ('other', 'Autre'),
]

# Types de documents disponibles
DOCUMENT_TYPES = [
    ('contract', 'Contrat de travail', 'fa-file-signature', '#6366f1'),
    ('payslip', 'Fiche de paie', 'fa-file-invoice-dollar', '#10b981'),
    ('expense_report', 'Fiche de frais', 'fa-receipt', '#ec4899'),
    ('certificate', 'Attestation', 'fa-certificate', '#f59e0b'),
    ('amendment', 'Avenant', 'fa-file-contract', '#8b5cf6'),
    ('other', 'Autre document', 'fa-file', '#6c757d'),
]

# Mois en français
MONTHS_FR = [
    (1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'),
    (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'),
    (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')
]


def get_document_type_info(type_code):
    """Retourne les informations d'un type de document"""
    for code, name, icon, color in DOCUMENT_TYPES:
        if code == type_code:
            return {'code': code, 'name': name, 'icon': icon, 'color': color}
    return {'code': 'other', 'name': 'Autre', 'icon': 'fa-file', 'color': '#6c757d'}


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

        flash(f'L\'employeur "{name}" a été ajouté avec succès !', 'success')
        return redirect(url_for('employers.detail', employer_id=employer.id))

    return render_template('employers/add.html', contract_types=CONTRACT_TYPES)


@bp.route('/<int:employer_id>')
@login_required
def detail(employer_id):
    employer = Employer.query.get_or_404(employer_id)

    if employer.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cet employeur.', 'danger')
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
    for doc_type, _, _, _ in DOCUMENT_TYPES:
        doc_counts[doc_type] = employer.documents.filter_by(document_type=doc_type).count()

    # Calculer la taille totale des documents
    total_size = db.session.query(db.func.sum(EmployerDocument.file_size)).filter(
        EmployerDocument.employer_id == employer_id
    ).scalar() or 0

    return render_template('employers/detail.html',
                         employer=employer,
                         documents=documents,
                         document_types=DOCUMENT_TYPES,
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
        flash('Vous n\'avez pas accès à cet employeur.', 'danger')
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

        flash(f'L\'employeur "{employer.name}" a été mis à jour.', 'success')
        return redirect(url_for('employers.detail', employer_id=employer.id))

    return render_template('employers/edit.html',
                         employer=employer,
                         contract_types=CONTRACT_TYPES)


@bp.route('/<int:employer_id>/delete', methods=['POST'])
@login_required
def delete(employer_id):
    employer = Employer.query.get_or_404(employer_id)

    if employer.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cet employeur.', 'danger')
        return redirect(url_for('employers.list'))

    employer_name = employer.name
    db.session.delete(employer)
    db.session.commit()

    flash(f'L\'employeur "{employer_name}" a été supprimé.', 'success')
    return redirect(url_for('employers.list'))


# Routes pour les documents
@bp.route('/<int:employer_id>/documents/add', methods=['GET', 'POST'])
@login_required
def add_document(employer_id):
    employer = Employer.query.get_or_404(employer_id)

    if employer.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cet employeur.', 'danger')
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

        # Gestion du fichier
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                document.file_data = file.read()
                document.file_name = file.filename
                document.file_mime_type = file.content_type
                document.file_size = len(document.file_data)

        db.session.add(document)
        db.session.commit()

        flash(f'Le document "{name}" a été ajouté avec succès !', 'success')
        return redirect(url_for('employers.detail', employer_id=employer_id))

    current_year = datetime.now().year
    years = list(range(current_year, current_year - 20, -1))

    return render_template('employers/add_document.html',
                         employer=employer,
                         document_types=DOCUMENT_TYPES,
                         months=MONTHS_FR,
                         years=years)


@bp.route('/documents/<int:document_id>/download')
@login_required
def download_document(document_id):
    document = EmployerDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce document.', 'danger')
        return redirect(url_for('employers.list'))

    if not document.file_data:
        flash('Ce document n\'a pas de fichier attaché.', 'warning')
        return redirect(url_for('employers.detail', employer_id=document.employer_id))

    return Response(
        document.file_data,
        mimetype=document.file_mime_type or 'application/octet-stream',
        headers={'Content-Disposition': f'attachment; filename="{document.file_name}"'}
    )


@bp.route('/documents/<int:document_id>/view')
@login_required
def view_document(document_id):
    document = EmployerDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce document.', 'danger')
        return redirect(url_for('employers.list'))

    if not document.file_data:
        flash('Ce document n\'a pas de fichier attaché.', 'warning')
        return redirect(url_for('employers.detail', employer_id=document.employer_id))

    return Response(
        document.file_data,
        mimetype=document.file_mime_type or 'application/octet-stream',
        headers={'Content-Disposition': f'inline; filename="{document.file_name}"'}
    )


@bp.route('/documents/<int:document_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_document(document_id):
    document = EmployerDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce document.', 'danger')
        return redirect(url_for('employers.list'))

    if request.method == 'POST':
        document.name = request.form.get('name')
        document.description = request.form.get('description')
        document.document_type = request.form.get('document_type')
        document.year = request.form.get('year', type=int)
        document.month = request.form.get('month', type=int)

        document_date_str = request.form.get('document_date')
        document.document_date = datetime.strptime(document_date_str, '%Y-%m-%d').date() if document_date_str else None

        # Gestion du fichier
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                document.file_data = file.read()
                document.file_name = file.filename
                document.file_mime_type = file.content_type
                document.file_size = len(document.file_data)

        db.session.commit()

        flash(f'Le document "{document.name}" a été mis à jour.', 'success')
        return redirect(url_for('employers.detail', employer_id=document.employer_id))

    current_year = datetime.now().year
    years = list(range(current_year, current_year - 20, -1))

    return render_template('employers/edit_document.html',
                         document=document,
                         employer=document.employer,
                         document_types=DOCUMENT_TYPES,
                         months=MONTHS_FR,
                         years=years)


@bp.route('/documents/<int:document_id>/delete', methods=['POST'])
@login_required
def delete_document(document_id):
    document = EmployerDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce document.', 'danger')
        return redirect(url_for('employers.list'))

    employer_id = document.employer_id
    document_name = document.name
    db.session.delete(document)
    db.session.commit()

    flash(f'Le document "{document_name}" a été supprimé.', 'success')
    return redirect(url_for('employers.detail', employer_id=employer_id))
