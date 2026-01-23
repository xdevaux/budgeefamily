"""
Routes pour gérer les banques
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_required, current_user
from datetime import datetime
from app import db, limiter
from app.models import Bank, BankDocument
from app.utils.file_security import validate_upload, get_safe_content_disposition
import base64

bp = Blueprint('banks', __name__, url_prefix='/banks')

# Types de documents disponibles pour les banques
DOCUMENT_TYPES = [
    ('rib', 'RIB', 'fa-file-invoice', '#6366f1'),
    ('contract', 'Contrat', 'fa-file-signature', '#10b981'),
    ('statement', 'Relevé', 'fa-file-invoice-dollar', '#f59e0b'),
    ('correspondence', 'Courrier', 'fa-envelope', '#06b6d4'),
    ('other', 'Autre document', 'fa-file', '#6c757d'),
]

# Mois en français
MONTHS_FR = [
    (1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'),
    (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'),
    (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')
]

# Logos des banques françaises
FRENCH_BANKS_LOGOS = {
    'BNP Paribas': {'color': '#00965E', 'initials': 'BNP', 'bic': 'BNPAFRPP'},
    'Crédit Agricole': {'color': '#00965E', 'initials': 'CA', 'bic': 'AGRIFRPP'},
    'Société Générale': {'color': '#E30513', 'initials': 'SG', 'bic': 'SOGEFRPP'},
    'Crédit Mutuel': {'color': '#003D7A', 'initials': 'CM', 'bic': 'CMCIFRPP'},
    'Banque Postale': {'color': '#FFD200', 'initials': 'LBP', 'bic': 'PSSTFRPP', 'text_color': '#003D7A'},
    'Caisse d\'Épargne': {'color': '#00965E', 'initials': 'CE', 'bic': 'CEPAFRPP'},
    'LCL': {'color': '#003D7A', 'initials': 'LCL', 'bic': 'CRLYFRPP'},
    'CIC': {'color': '#003D7A', 'initials': 'CIC', 'bic': 'CMCIFRPP'},
    'BoursoBank': {'color': '#0E52A0', 'initials': 'BRS', 'bic': 'BOUSFRPP'},
    'Banque Populaire': {'color': '#E30513', 'initials': 'BP', 'bic': 'CCBPFRPP'},
    'Hello bank!': {'color': '#FF6600', 'initials': 'HB', 'bic': 'BNPAFRPP'},
    'ING Direct': {'color': '#FF6200', 'initials': 'ING', 'bic': 'INGBFRPP'},
    'Fortuneo': {'color': '#8B0000', 'initials': 'FTN', 'bic': 'FTNOFRP1'},
    'Monabanq': {'color': '#00A651', 'initials': 'MNB', 'bic': 'CMCIFRPP'},
    'N26': {'color': '#36A18B', 'initials': 'N26', 'bic': 'NTSBDEB1'},
    'Revolut': {'color': '#0075EB', 'initials': 'RVL', 'bic': 'REVOGB21'},
}


def generate_bank_logo_svg(bank_name, color, initials, text_color='#FFFFFF'):
    """Génère un logo SVG simple pour une banque"""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
        <rect width="200" height="200" rx="20" fill="{color}"/>
        <text x="100" y="115" font-family="Arial, sans-serif" font-size="60" font-weight="bold"
              fill="{text_color}" text-anchor="middle">{initials}</text>
    </svg>'''
    return base64.b64encode(svg.encode('utf-8')).decode('utf-8')


def get_document_type_info(type_code):
    """Retourne les informations d'un type de document"""
    for code, name, icon, color in DOCUMENT_TYPES:
        if code == type_code:
            return {'code': code, 'name': name, 'icon': icon, 'color': color}
    return {'code': 'other', 'name': 'Autre', 'icon': 'fa-file', 'color': '#6c757d'}


@bp.route('/')
@login_required
def list_banks():
    """Liste des banques de l'utilisateur"""
    page = request.args.get('page', 1, type=int)
    filter_status = request.args.get('status', 'all')

    query = Bank.query.filter_by(user_id=current_user.id)

    if filter_status == 'active':
        query = query.filter_by(is_active=True)
    elif filter_status == 'inactive':
        query = query.filter_by(is_active=False)

    banks = query.order_by(Bank.name).paginate(
        page=page, per_page=10, error_out=False
    )

    return render_template('banks/list.html', banks=banks, filter_status=filter_status)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Ajouter une nouvelle banque"""
    if request.method == 'POST':
        bank = Bank(
            user_id=current_user.id,
            name=request.form.get('name'),
            address=request.form.get('address'),
            postal_code=request.form.get('postal_code'),
            city=request.form.get('city'),
            country=request.form.get('country'),
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            website=request.form.get('website'),
            account_number=request.form.get('account_number'),
            iban=request.form.get('iban'),
            bic=request.form.get('bic'),
            notes=request.form.get('notes')
        )

        # Gestion du logo uploadé
        if 'logo' in request.files:
            logo_file = request.files['logo']
            if logo_file and logo_file.filename:
                logo_data = base64.b64encode(logo_file.read()).decode('utf-8')
                bank.logo_data = logo_data
                bank.logo_mime_type = logo_file.content_type

        db.session.add(bank)
        db.session.commit()

        flash('Banque ajoutée avec succès !', 'success')
        return redirect(url_for('banks.detail', bank_id=bank.id))

    return render_template('banks/add.html', french_banks=FRENCH_BANKS_LOGOS)


@bp.route('/<int:bank_id>')
@login_required
def detail(bank_id):
    """Détails d'une banque"""
    bank = Bank.query.get_or_404(bank_id)

    if bank.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cette banque.', 'danger')
        return redirect(url_for('banks.list_banks'))

    # Récupérer les documents avec filtres
    filter_type = request.args.get('doc_type', None)
    filter_year = request.args.get('year', None, type=int)
    search = request.args.get('search', None)

    query = bank.documents

    if filter_type:
        query = query.filter_by(document_type=filter_type)
    if filter_year:
        query = query.filter_by(year=filter_year)
    if search:
        query = query.filter(BankDocument.name.ilike(f'%{search}%'))

    documents = query.order_by(BankDocument.year.desc(), BankDocument.month.desc(), BankDocument.document_date.desc()).all()

    # Obtenir les années disponibles pour le filtre
    years = db.session.query(BankDocument.year).filter(
        BankDocument.bank_id == bank_id,
        BankDocument.year.isnot(None)
    ).distinct().order_by(BankDocument.year.desc()).all()
    years = [y[0] for y in years]

    # Compter les documents par type
    doc_counts = {}
    for doc_type, _, _, _ in DOCUMENT_TYPES:
        doc_counts[doc_type] = bank.documents.filter_by(document_type=doc_type).count()

    # Calculer la taille totale des documents
    total_size = db.session.query(db.func.sum(BankDocument.file_size)).filter(
        BankDocument.bank_id == bank_id
    ).scalar() or 0

    return render_template('banks/detail.html',
                         bank=bank,
                         documents=documents,
                         document_types=DOCUMENT_TYPES,
                         years=years,
                         filter_type=filter_type,
                         filter_year=filter_year,
                         search=search,
                         doc_counts=doc_counts,
                         total_size=total_size,
                         get_document_type_info=get_document_type_info)


@bp.route('/<int:bank_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(bank_id):
    """Modifier une banque"""
    bank = Bank.query.get_or_404(bank_id)

    if bank.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cette banque.', 'danger')
        return redirect(url_for('banks.list_banks'))

    if request.method == 'POST':
        bank.name = request.form.get('name')
        bank.address = request.form.get('address')
        bank.postal_code = request.form.get('postal_code')
        bank.city = request.form.get('city')
        bank.country = request.form.get('country')
        bank.phone = request.form.get('phone')
        bank.email = request.form.get('email')
        bank.website = request.form.get('website')
        bank.account_number = request.form.get('account_number')
        bank.iban = request.form.get('iban')
        bank.bic = request.form.get('bic')
        bank.notes = request.form.get('notes')
        bank.updated_at = datetime.utcnow()

        # Supprimer le logo si demandé
        if request.form.get('remove_logo') == '1':
            bank.logo_data = None
            bank.logo_mime_type = None

        # Gestion du logo uploadé
        if 'logo' in request.files:
            logo_file = request.files['logo']
            if logo_file and logo_file.filename:
                logo_data = base64.b64encode(logo_file.read()).decode('utf-8')
                bank.logo_data = logo_data
                bank.logo_mime_type = logo_file.content_type

        db.session.commit()

        flash('Banque modifiée avec succès !', 'success')
        return redirect(url_for('banks.detail', bank_id=bank.id))

    return render_template('banks/edit.html', bank=bank)


@bp.route('/<int:bank_id>/toggle', methods=['POST'])
@login_required
def toggle(bank_id):
    """Activer/Désactiver une banque"""
    bank = Bank.query.get_or_404(bank_id)

    if bank.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cette banque.', 'danger')
        return redirect(url_for('banks.list_banks'))

    bank.is_active = not bank.is_active
    db.session.commit()

    status = 'activée' if bank.is_active else 'désactivée'
    flash(f'La banque "{bank.name}" a été {status}.', 'success')
    return redirect(url_for('banks.list_banks'))


@bp.route('/<int:bank_id>/delete', methods=['POST'])
@login_required
def delete(bank_id):
    """Supprimer une banque"""
    bank = Bank.query.get_or_404(bank_id)

    if bank.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cette banque.', 'danger')
        return redirect(url_for('banks.list_banks'))

    # Vérifier si la banque est utilisée par des crédits
    if bank.credits.count() > 0:
        flash('Impossible de supprimer cette banque car elle est utilisée par des crédits.', 'warning')
        return redirect(url_for('banks.list_banks'))

    db.session.delete(bank)
    db.session.commit()

    flash('Banque supprimée avec succès !', 'success')
    return redirect(url_for('banks.list_banks'))


@bp.route('/api/list')
@login_required
def api_list():
    """API pour récupérer la liste des banques (pour les selects)"""
    banks = Bank.query.filter_by(user_id=current_user.id, is_active=True).order_by(Bank.name).all()
    return jsonify([{
        'id': bank.id,
        'name': bank.name
    } for bank in banks])


# Routes pour les documents
@bp.route('/<int:bank_id>/documents/add', methods=['GET', 'POST'])
@login_required
@limiter.limit("100 per hour")
def add_document(bank_id):
    bank = Bank.query.get_or_404(bank_id)

    if bank.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cette banque.', 'danger')
        return redirect(url_for('banks.list_banks'))

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

        document = BankDocument(
            user_id=current_user.id,
            bank_id=bank_id,
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
                # Validation stricte du fichier
                success, error, file_data, safe_filename = validate_upload(file)

                if not success:
                    flash(error, 'danger')
                    return redirect(url_for('banks.add_document', bank_id=bank_id))

                document.file_data = file_data
                document.file_name = safe_filename
                document.file_mime_type = file.content_type
                document.file_size = len(file_data)

        db.session.add(document)
        db.session.commit()

        flash(f'Le document "{name}" a été ajouté avec succès !', 'success')
        return redirect(url_for('banks.detail', bank_id=bank_id))

    current_year = datetime.now().year
    years = list(range(current_year, current_year - 20, -1))

    return render_template('banks/add_document.html',
                         bank=bank,
                         document_types=DOCUMENT_TYPES,
                         months=MONTHS_FR,
                         years=years)


@bp.route('/documents/<int:document_id>/download')
@login_required
def download_document(document_id):
    document = BankDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce document.', 'danger')
        return redirect(url_for('banks.list_banks'))

    if not document.file_data:
        flash('Ce document n\'a pas de fichier attaché.', 'warning')
        return redirect(url_for('banks.detail', bank_id=document.bank_id))

    return Response(
        document.file_data,
        mimetype=document.file_mime_type or 'application/octet-stream',
        headers={'Content-Disposition': get_safe_content_disposition(document.file_name, inline=False)}
    )


@bp.route('/documents/<int:document_id>/view')
@login_required
def view_document(document_id):
    document = BankDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce document.', 'danger')
        return redirect(url_for('banks.list_banks'))

    if not document.file_data:
        flash('Ce document n\'a pas de fichier attaché.', 'warning')
        return redirect(url_for('banks.detail', bank_id=document.bank_id))

    return Response(
        document.file_data,
        mimetype=document.file_mime_type or 'application/octet-stream',
        headers={'Content-Disposition': get_safe_content_disposition(document.file_name, inline=True)}
    )


@bp.route('/documents/<int:document_id>/edit', methods=['GET', 'POST'])
@login_required
@limiter.limit("100 per hour")
def edit_document(document_id):
    document = BankDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce document.', 'danger')
        return redirect(url_for('banks.list_banks'))

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
                # Validation stricte du fichier
                success, error, file_data, safe_filename = validate_upload(file)

                if not success:
                    flash(error, 'danger')
                    return redirect(url_for('banks.edit_document', document_id=document_id))

                document.file_data = file_data
                document.file_name = safe_filename
                document.file_mime_type = file.content_type
                document.file_size = len(file_data)

        db.session.commit()

        flash(f'Le document "{document.name}" a été mis à jour.', 'success')
        return redirect(url_for('banks.detail', bank_id=document.bank_id))

    current_year = datetime.now().year
    years = list(range(current_year, current_year - 20, -1))

    return render_template('banks/edit_document.html',
                         document=document,
                         bank=document.bank,
                         document_types=DOCUMENT_TYPES,
                         months=MONTHS_FR,
                         years=years)


@bp.route('/documents/<int:document_id>/delete', methods=['POST'])
@login_required
def delete_document(document_id):
    document = BankDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash('Vous n\'avez pas accès à ce document.', 'danger')
        return redirect(url_for('banks.list_banks'))

    bank_id = document.bank_id
    document_name = document.name
    db.session.delete(document)
    db.session.commit()

    flash(f'Le document "{document_name}" a été supprimé.', 'success')
    return redirect(url_for('banks.detail', bank_id=bank_id))
