from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from app import db, limiter
from app.models import Reminder, ReminderDocument, Provider
from app.utils.file_security import validate_upload, get_safe_content_disposition
from datetime import datetime, date
from sqlalchemy import or_, and_

bp = Blueprint('reminders', __name__, url_prefix='/reminders')

# Document types available for reminders
DOCUMENT_TYPES = [
    ('invoice', 'Invoice', 'fa-file-invoice', '#10b981'),
    ('contract', 'Contract', 'fa-file-signature', '#6366f1'),
    ('report', 'Report/Certificate', 'fa-file-alt', '#f59e0b'),
    ('certificate', 'Certificate', 'fa-certificate', '#8b5cf6'),
    ('other', 'Other document', 'fa-file', '#6c757d'),
]

# Recurrence types
RECURRENCE_TYPES = [
    ('weekly', 'Weekly'),
    ('monthly', 'Monthly'),
    ('quarterly', 'Quarterly (every 3 months)'),
    ('semiannual', 'Semiannual (every 6 months)'),
    ('annual', 'Annual'),
    ('biennial', 'Biennial (every 2 years)'),
    ('once', 'Once (one time only)'),
]

# Months in English
MONTHS = [
    (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
    (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
    (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
]


def get_document_type_info(type_code):
    """Returns information for a document type"""
    for code, name, icon, color in DOCUMENT_TYPES:
        if code == type_code:
            return {'code': code, 'name': name, 'icon': icon, 'color': color}
    return {'code': 'other', 'name': 'Other', 'icon': 'fa-file', 'color': '#6c757d'}


@bp.route('/', endpoint='list')
@login_required
def reminder_list():
    page = request.args.get('page', 1, type=int)
    filter_status = request.args.get('status', 'active')
    provider_id = request.args.get('provider_id', type=int)

    query = current_user.reminders

    if filter_status == 'active':
        query = query.filter_by(is_active=True)
    elif filter_status == 'archived':
        query = query.filter_by(is_active=False)

    if provider_id:
        query = query.filter_by(provider_id=provider_id)

    reminders = query.order_by(Reminder.reminder_year, Reminder.reminder_month).paginate(
        page=page, per_page=10, error_out=False
    )

    providers = current_user.providers.filter_by(is_active=True).all()

    return render_template('reminders/list.html',
                         reminders=reminders,
                         filter_status=filter_status,
                         providers=providers,
                         selected_provider=provider_id)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if not current_user.can_add_reminder():
        flash('Reminder limit reached. Upgrade to Premium to add more.', 'warning')
        return redirect(url_for('reminders.list'))

    if request.method == 'POST':
        name = request.form.get('name')
        provider_id = request.form.get('provider_id', type=int) or None
        reminder_month = int(request.form.get('reminder_month'))
        reminder_year = int(request.form.get('reminder_year'))
        estimated_cost = float(request.form.get('estimated_cost', 0) or 0)
        recurrence = request.form.get('recurrence', 'annual')
        description = request.form.get('description')

        reminder = Reminder(
            user_id=current_user.id,
            name=name,
            provider_id=provider_id,
            reminder_month=reminder_month,
            reminder_year=reminder_year,
            estimated_cost=estimated_cost,
            recurrence=recurrence,
            description=description
        )

        db.session.add(reminder)
        db.session.commit()

        flash(f'The reminder "{reminder.name}" has been added.', 'success')
        return redirect(url_for('reminders.detail', reminder_id=reminder.id))

    providers = current_user.providers.filter_by(is_active=True).all()
    current_year = datetime.now().year
    years = list(range(current_year, current_year + 10))

    return render_template('reminders/add.html',
                         recurrence_types=RECURRENCE_TYPES,
                         providers=providers,
                         months=MONTHS,
                         years=years)


@bp.route('/<int:reminder_id>')
@login_required
def detail(reminder_id):
    reminder = Reminder.query.get_or_404(reminder_id)

    if reminder.user_id != current_user.id:
        flash('You do not have access to this reminder.', 'danger')
        return redirect(url_for('reminders.list'))

    # Retrieve ALL reminders for the same service (same provider_id and same name)
    # to display all associated documents
    related_reminder_ids = db.session.query(Reminder.id).filter(
        Reminder.user_id == current_user.id,
        Reminder.provider_id == reminder.provider_id,
        Reminder.name == reminder.name
    ).all()
    related_reminder_ids = [r[0] for r in related_reminder_ids]

    # Retrieve documents with filters
    filter_type = request.args.get('doc_type', None)
    filter_year = request.args.get('year', None, type=int)
    search = request.args.get('search', None)

    # Query all documents from related reminders (active AND archived)
    query = ReminderDocument.query.filter(
        ReminderDocument.reminder_id.in_(related_reminder_ids)
    )

    if filter_type:
        query = query.filter_by(document_type=filter_type)
    if filter_year:
        query = query.filter_by(year=filter_year)
    if search:
        query = query.filter(ReminderDocument.name.ilike(f'%{search}%'))

    documents = query.order_by(ReminderDocument.year.desc(), ReminderDocument.month.desc(), ReminderDocument.document_date.desc()).all()

    # Get available years for filter
    years = db.session.query(ReminderDocument.year).filter(
        ReminderDocument.reminder_id.in_(related_reminder_ids),
        ReminderDocument.year.isnot(None)
    ).distinct().order_by(ReminderDocument.year.desc()).all()
    years = [y[0] for y in years]

    # Count documents by type (across all related reminders)
    doc_counts = {}
    for doc_type, _, _, _ in DOCUMENT_TYPES:
        doc_counts[doc_type] = ReminderDocument.query.filter(
            ReminderDocument.reminder_id.in_(related_reminder_ids),
            ReminderDocument.document_type == doc_type
        ).count()

    # Calculate total size of documents (across all related reminders)
    total_size = db.session.query(db.func.sum(ReminderDocument.file_size)).filter(
        ReminderDocument.reminder_id.in_(related_reminder_ids)
    ).scalar() or 0

    return render_template('reminders/detail.html',
                         reminder=reminder,
                         documents=documents,
                         document_types=DOCUMENT_TYPES,
                         years=years,
                         filter_type=filter_type,
                         filter_year=filter_year,
                         search=search,
                         doc_counts=doc_counts,
                         total_size=total_size,
                         get_document_type_info=get_document_type_info)


@bp.route('/<int:reminder_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(reminder_id):
    reminder = Reminder.query.get_or_404(reminder_id)

    if reminder.user_id != current_user.id:
        flash('You do not have access to this reminder.', 'danger')
        return redirect(url_for('reminders.list'))

    if request.method == 'POST':
        reminder.name = request.form.get('name')
        reminder.provider_id = request.form.get('provider_id', type=int) or None
        reminder.reminder_month = int(request.form.get('reminder_month'))
        reminder.reminder_year = int(request.form.get('reminder_year'))
        reminder.estimated_cost = float(request.form.get('estimated_cost', 0) or 0)
        reminder.recurrence = request.form.get('recurrence', 'annual')
        reminder.description = request.form.get('description')

        db.session.commit()

        flash(f'The reminder "{reminder.name}" has been updated.', 'success')
        return redirect(url_for('reminders.detail', reminder_id=reminder.id))

    providers = current_user.providers.filter_by(is_active=True).all()
    current_year = datetime.now().year
    years = list(range(current_year, current_year + 10))

    return render_template('reminders/edit.html',
                         reminder=reminder,
                         recurrence_types=RECURRENCE_TYPES,
                         providers=providers,
                         months=MONTHS,
                         years=years)


@bp.route('/<int:reminder_id>/delete', methods=['POST'])
@login_required
def delete(reminder_id):
    reminder = Reminder.query.get_or_404(reminder_id)

    if reminder.user_id != current_user.id:
        flash('You do not have access to this reminder.', 'danger')
        return redirect(url_for('reminders.list'))

    name = reminder.name
    db.session.delete(reminder)
    db.session.commit()

    flash(f'The reminder "{name}" has been deleted.', 'success')
    return redirect(url_for('reminders.list'))


@bp.route('/<int:reminder_id>/toggle-appointment', methods=['POST'])
@login_required
def toggle_appointment(reminder_id):
    reminder = Reminder.query.get_or_404(reminder_id)

    if reminder.user_id != current_user.id:
        flash('You do not have access to this reminder.', 'danger')
        return redirect(url_for('reminders.list'))

    reminder.appointment_booked = not reminder.appointment_booked

    if reminder.appointment_booked:
        appointment_date_str = request.form.get('appointment_date')
        if appointment_date_str:
            reminder.appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%d').date()
    else:
        reminder.appointment_date = None

    db.session.commit()

    status = "booked" if reminder.appointment_booked else "cancelled"
    flash(f'Appointment {status}.', 'success')

    return redirect(url_for('reminders.detail', reminder_id=reminder.id))


@bp.route('/<int:reminder_id>/archive', methods=['POST'])
@login_required
def archive(reminder_id):
    reminder = Reminder.query.get_or_404(reminder_id)

    if reminder.user_id != current_user.id:
        flash('You do not have access to this reminder.', 'danger')
        return redirect(url_for('reminders.list'))

    # Archive current reminder
    reminder.is_active = False
    reminder.archived_at = datetime.utcnow()

    # Create new reminder if recurring
    if reminder.recurrence != 'once':
        from dateutil.relativedelta import relativedelta

        # Calculate date of next reminder
        current_date = date(reminder.reminder_year, reminder.reminder_month, 1)

        if reminder.recurrence == 'weekly':
            next_date = current_date + relativedelta(weeks=1)
        elif reminder.recurrence == 'monthly':
            next_date = current_date + relativedelta(months=1)
        elif reminder.recurrence == 'quarterly':
            next_date = current_date + relativedelta(months=3)
        elif reminder.recurrence == 'semiannual':
            next_date = current_date + relativedelta(months=6)
        elif reminder.recurrence == 'annual':
            next_date = current_date + relativedelta(years=1)
        elif reminder.recurrence == 'biennial':
            next_date = current_date + relativedelta(years=2)

        next_year = next_date.year
        next_month = next_date.month

        # Create new reminder
        new_reminder = Reminder(
            user_id=reminder.user_id,
            provider_id=reminder.provider_id,
            name=reminder.name,
            description=reminder.description,
            reminder_month=next_month,
            reminder_year=next_year,
            estimated_cost=reminder.estimated_cost,
            recurrence=reminder.recurrence,
            appointment_booked=False,
            appointment_date=None
        )
        db.session.add(new_reminder)

    db.session.commit()

    flash(f'The reminder "{reminder.name}" has been archived.', 'success')
    return redirect(url_for('reminders.list'))


@bp.route('/<int:reminder_id>/unarchive', methods=['POST'])
@login_required
def unarchive(reminder_id):
    reminder = Reminder.query.get_or_404(reminder_id)

    if reminder.user_id != current_user.id:
        flash('You do not have access to this reminder.', 'danger')
        return redirect(url_for('reminders.list'))

    # Unarchive the reminder
    reminder.is_active = True
    reminder.archived_at = None

    db.session.commit()

    flash(f'The reminder "{reminder.name}" has been unarchived.', 'success')
    return redirect(url_for('reminders.list'))


# ==================== DOCUMENT MANAGEMENT ====================

@bp.route('/<int:reminder_id>/documents/add', methods=['GET', 'POST'])
@login_required
@limiter.limit("100 per hour")
def add_document(reminder_id):
    reminder = Reminder.query.get_or_404(reminder_id)

    if reminder.user_id != current_user.id:
        flash('You do not have access to this reminder.', 'danger')
        return redirect(url_for('reminders.list'))

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

        # Auto-fill year and month from date if not provided
        if document_date and not year:
            year = document_date.year
        if document_date and not month:
            month = document_date.month

        document = ReminderDocument(
            user_id=current_user.id,
            reminder_id=reminder_id,
            name=name,
            description=description,
            document_type=document_type,
            document_date=document_date,
            year=year,
            month=month
        )

        # File handling with security validation
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                success, error, file_data, safe_filename = validate_upload(file)
                if not success:
                    flash(error, 'danger')
                    return redirect(url_for('reminders.add_document', reminder_id=reminder_id))

                document.file_data = file_data
                document.file_name = safe_filename
                document.file_mime_type = file.content_type
                document.file_size = len(file_data)

        db.session.add(document)
        db.session.commit()

        flash(f'The document "{name}" has been added successfully!', 'success')
        return redirect(url_for('reminders.detail', reminder_id=reminder_id))

    current_year = datetime.now().year
    years = list(range(current_year, current_year - 20, -1))

    return render_template('reminders/add_document.html',
                         reminder=reminder,
                         document_types=DOCUMENT_TYPES,
                         months=MONTHS,
                         years=years)


@bp.route('/documents/<int:document_id>/view')
@login_required
def view_document(document_id):
    document = ReminderDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash('You do not have access to this document.', 'danger')
        return redirect(url_for('reminders.list'))

    if not document.file_data:
        flash('This document does not have an attached file.', 'warning')
        return redirect(url_for('reminders.detail', reminder_id=document.reminder_id))

    return Response(
        document.file_data,
        mimetype=document.file_mime_type or 'application/octet-stream',
        headers={'Content-Disposition': get_safe_content_disposition(document.file_name, inline=True)}
    )


@bp.route('/documents/<int:document_id>/download')
@login_required
def download_document(document_id):
    document = ReminderDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash('You do not have access to this document.', 'danger')
        return redirect(url_for('reminders.list'))

    if not document.file_data:
        flash('This document does not have an attached file.', 'warning')
        return redirect(url_for('reminders.detail', reminder_id=document.reminder_id))

    return Response(
        document.file_data,
        mimetype=document.file_mime_type or 'application/octet-stream',
        headers={'Content-Disposition': get_safe_content_disposition(document.file_name, inline=False)}
    )


@bp.route('/documents/<int:document_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_document(document_id):
    document = ReminderDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash('You do not have access to this document.', 'danger')
        return redirect(url_for('reminders.list'))

    if request.method == 'POST':
        document.name = request.form.get('name')
        document.description = request.form.get('description')
        document.document_type = request.form.get('document_type')
        document.year = request.form.get('year', type=int)
        document.month = request.form.get('month', type=int)

        document_date_str = request.form.get('document_date')
        document.document_date = datetime.strptime(document_date_str, '%Y-%m-%d').date() if document_date_str else None

        # File handling with security validation
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                success, error, file_data, safe_filename = validate_upload(file)
                if not success:
                    flash(error, 'danger')
                    return redirect(url_for('reminders.edit_document', document_id=document_id))

                document.file_data = file_data
                document.file_name = safe_filename
                document.file_mime_type = file.content_type
                document.file_size = len(file_data)

        db.session.commit()

        flash(f'The document "{document.name}" has been updated.', 'success')
        return redirect(url_for('reminders.detail', reminder_id=document.reminder_id))

    current_year = datetime.now().year
    years = list(range(current_year, current_year - 20, -1))

    return render_template('reminders/edit_document.html',
                         document=document,
                         reminder=document.reminder,
                         document_types=DOCUMENT_TYPES,
                         months=MONTHS,
                         years=years)


@bp.route('/documents/<int:document_id>/delete', methods=['POST'])
@login_required
def delete_document(document_id):
    document = ReminderDocument.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash('You do not have access to this document.', 'danger')
        return redirect(url_for('reminders.list'))

    reminder_id = document.reminder_id
    document_name = document.name
    db.session.delete(document)
    db.session.commit()

    flash(f'The document "{document_name}" has been deleted.', 'success')
    return redirect(url_for('reminders.detail', reminder_id=reminder_id))
