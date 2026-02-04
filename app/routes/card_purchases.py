from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, jsonify
from flask_login import login_required, current_user
from app import db, limiter
from app.models import CardPurchase, Category, Transaction
from app.utils.file_security import validate_upload, get_safe_content_disposition
from app.utils.ocr_processor import process_receipt_ocr
from datetime import datetime
import json
import base64

bp = Blueprint('card_purchases', __name__, url_prefix='/card-purchases')


@bp.route('/')
@login_required
def list_purchases():
    """List all user's card purchases"""
    page = request.args.get('page', 1, type=int)
    filter_category = request.args.get('category', None, type=int)

    # Set default filters to current month and year if no parameters in URL
    current_month = datetime.now().month
    current_year = datetime.now().year

    # If no month/year parameters present, use current month/year
    # Otherwise, use what is provided (can be None if user chooses "All")
    if 'month' not in request.args and 'year' not in request.args:
        filter_month = current_month
        filter_year = current_year
    else:
        filter_month = request.args.get('month', type=int) if request.args.get('month') else None
        filter_year = request.args.get('year', type=int) if request.args.get('year') else None

    query = current_user.card_purchases.filter_by(is_active=True)

    # Filters
    if filter_category:
        query = query.filter_by(category_id=filter_category)
    if filter_month and filter_year:
        query = query.filter(
            db.extract('month', CardPurchase.purchase_date) == filter_month,
            db.extract('year', CardPurchase.purchase_date) == filter_year
        )

    purchases = query.order_by(CardPurchase.purchase_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    # Get categories for filter (only those for card purchases or 'all')
    categories = Category.query.filter(
        db.or_(
            Category.user_id == current_user.id,
            Category.user_id == None
        ),
        db.or_(
            Category.category_type == 'card_purchase',
            Category.category_type == 'all'
        )
    ).filter_by(is_active=True).order_by(Category.name).all()

    return render_template('card_purchases/list.html',
                         purchases=purchases,
                         categories=categories,
                         filter_category=filter_category,
                         filter_month=filter_month,
                         filter_year=filter_year,
                         now=datetime.now())


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_manual():
    """Add a card purchase manually (default mode)"""

    # Get categories (only those for card purchases or 'all')
    categories = Category.query.filter(
        db.or_(
            Category.user_id == current_user.id,
            Category.user_id == None
        ),
        db.or_(
            Category.category_type == 'card_purchase',
            Category.category_type == 'all'
        )
    ).filter_by(is_active=True).order_by(Category.name).all()

    if request.method == 'POST':
        try:
            # Get form data
            merchant_name = request.form.get('merchant_name')
            amount = float(request.form.get('amount'))
            purchase_date = request.form.get('purchase_date')
            purchase_time = request.form.get('purchase_time', '12:00')
            category_id = request.form.get('category_id', type=int)
            payment_type = request.form.get('payment_type', 'card')
            description = request.form.get('description', '')

            # Create card purchase
            purchase = CardPurchase(
                user_id=current_user.id,
                purchase_date=datetime.strptime(f'{purchase_date} {purchase_time}', '%Y-%m-%d %H:%M'),
                merchant_name=merchant_name,
                amount=amount,
                currency='EUR',
                payment_type=payment_type,
                description=description,
                ocr_confidence=0,  # No OCR
                was_manually_edited=True,
                entry_method='manual',  # Manual entry
            )

            # Associate a category if selected
            if category_id:
                category = Category.query.get(category_id)
                if category:
                    purchase.category_id = category_id
                    purchase.category_name = category.name

            # Handle uploaded receipt (optional)
            receipt_file = request.files.get('receipt_file')
            if receipt_file and receipt_file.filename:
                # Validate file
                is_valid, error_message, file_data, safe_filename = validate_upload(receipt_file)
                if not is_valid:
                    flash(f'Error with receipt: {error_message}', 'warning')
                else:
                    # Store file
                    purchase.receipt_image_data = file_data
                    purchase.receipt_image_name = safe_filename
                    purchase.receipt_image_mime_type = receipt_file.content_type
                    purchase.receipt_image_size = len(file_data)

            db.session.add(purchase)
            db.session.flush()

            # Create transaction in balance
            transaction = Transaction(
                user_id=current_user.id,
                transaction_date=purchase.purchase_date.date(),
                transaction_type='card_purchase',
                source_id=purchase.id,
                source_type='card_purchase',
                name=f'Card Purchase - {purchase.merchant_name}',
                description=purchase.description,
                amount=purchase.amount,
                currency='EUR',
                is_positive=False,
                category_name=purchase.category_name,
                status='completed'
            )
            db.session.add(transaction)
            db.session.commit()

            flash('Card purchase added successfully!', 'success')
            return redirect(url_for('card_purchases.list_purchases'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error adding purchase: {str(e)}', 'danger')

    # GET: Display form
    return render_template('card_purchases/add_manual.html',
                         categories=categories,
                         today=datetime.now().strftime('%Y-%m-%d'))


@bp.route('/upload', methods=['GET', 'POST'])
@login_required
@limiter.limit("50 per hour")
def upload_receipts():
    """Multiple upload with OCR processing and validation grid"""

    # Check if user has Premium access
    if not current_user.is_premium():
        flash(_('La fonction OCR est réservée aux abonnés Premium.'), 'warning')
        return redirect(url_for('card_purchases.list_purchases'))

    if request.method == 'POST':
        # Get all uploaded files
        files = request.files.getlist('receipts')

        if not files or len(files) == 0:
            flash('No file selected.', 'warning')
            return redirect(url_for('card_purchases.upload_receipts'))

        # Limit to 10 files per upload
        if len(files) > 10:
            flash('Maximum 10 files per upload.', 'warning')
            return redirect(url_for('card_purchases.upload_receipts'))

        processed_receipts = []

        # Process each file
        for file in files:
            if not file or not file.filename:
                continue

            # Validate file
            success, error, file_data, safe_filename = validate_upload(file)

            if not success:
                flash(f'Error with {file.filename}: {error}', 'danger')
                continue

            # Process OCR
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"OCR processing {safe_filename} ({file.content_type}, {len(file_data)} bytes)")

                ocr_data = process_receipt_ocr(file_data)

                logger.info(f"OCR successful: {ocr_data['merchant_name']}, {ocr_data['amount']}€, confidence={ocr_data['ocr_confidence']:.1f}%")

                processed_receipts.append({
                    'file_data_base64': base64.b64encode(file_data).decode('utf-8'),
                    'file_name': safe_filename,
                    'file_mime_type': file.content_type,
                    'file_size': len(file_data),
                    'merchant_name': ocr_data['merchant_name'],
                    'amount': ocr_data['amount'],
                    'purchase_date': ocr_data['purchase_date'].strftime('%Y-%m-%d'),
                    'purchase_time': ocr_data['purchase_date'].strftime('%H:%M'),
                    'category_name': ocr_data['category_name'],
                    'ocr_confidence': ocr_data['ocr_confidence'],
                })
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'OCR error with {safe_filename}: {type(e).__name__}: {str(e)}')
                import traceback
                logger.error(traceback.format_exc())

                # More informative error message for user
                if 'PDF' in str(e) or safe_filename.lower().endswith('.pdf'):
                    flash(f'Error converting PDF "{file.filename}". Make sure the PDF is readable and contains text.', 'danger')
                else:
                    flash(f'OCR error with "{file.filename}": {str(e)}', 'danger')
                continue

        if not processed_receipts:
            flash('No valid receipt could be processed.', 'danger')
            return redirect(url_for('card_purchases.upload_receipts'))

        # Get categories for form (only those for card purchases or 'all')
        categories = Category.query.filter(
            db.or_(
                Category.user_id == current_user.id,
                Category.user_id == None
            ),
            db.or_(
                Category.category_type == 'card_purchase',
                Category.category_type == 'all'
            )
        ).filter_by(is_active=True).order_by(Category.name).all()

        return render_template('card_purchases/validate.html',
                             receipts=processed_receipts,
                             categories=categories)

    # GET: Display upload form
    return render_template('card_purchases/upload.html')


@bp.route('/validate', methods=['POST'])
@login_required
def validate_purchases():
    """Validate and save purchases after user modification"""

    # Check if user has Premium access
    if not current_user.is_premium():
        flash(_('La fonction OCR est réservée aux abonnés Premium.'), 'warning')
        return redirect(url_for('card_purchases.list_purchases'))

    # Get form data
    purchases_data = request.form.get('purchases_json')

    if not purchases_data:
        flash('No data to save.', 'danger')
        return redirect(url_for('card_purchases.upload_receipts'))

    try:
        purchases = json.loads(purchases_data)
    except json.JSONDecodeError:
        flash('Error processing data.', 'danger')
        return redirect(url_for('card_purchases.upload_receipts'))

    saved_count = 0

    for purchase_data in purchases:
        # Check if user wants to keep this purchase
        if not purchase_data.get('keep', True):
            continue

        # Decode image
        try:
            receipt_data = base64.b64decode(purchase_data['file_data_base64'])
        except Exception:
            receipt_data = None

        # Create card purchase
        purchase = CardPurchase(
            user_id=current_user.id,
            purchase_date=datetime.strptime(
                f"{purchase_data['purchase_date']} {purchase_data.get('purchase_time', '12:00')}",
                '%Y-%m-%d %H:%M'
            ),
            merchant_name=purchase_data['merchant_name'],
            amount=float(purchase_data['amount']),
            currency='EUR',
            payment_type=purchase_data.get('payment_type', 'card'),
            category_name=purchase_data.get('category_name'),
            description=purchase_data.get('description', ''),
            ocr_confidence=float(purchase_data.get('ocr_confidence', 0)),
            was_manually_edited=purchase_data.get('was_edited', False),
            entry_method='ocr',  # OCR entry
            receipt_image_data=receipt_data,
            receipt_image_name=purchase_data.get('file_name'),
            receipt_image_mime_type=purchase_data.get('file_mime_type'),
            receipt_image_size=purchase_data.get('file_size')
        )

        # Associate a category if possible
        if purchase_data.get('category_id'):
            category_id = int(purchase_data['category_id'])
            category = Category.query.get(category_id)
            if category:
                purchase.category_id = category_id
                purchase.category_name = category.name

        db.session.add(purchase)
        db.session.flush()

        # Create transaction in balance
        transaction = Transaction(
            user_id=current_user.id,
            transaction_date=purchase.purchase_date.date(),
            transaction_type='card_purchase',
            source_id=purchase.id,
            source_type='card_purchase',
            name=f'Card Purchase - {purchase.merchant_name}',
            description=purchase.description,
            amount=purchase.amount,
            currency='EUR',
            is_positive=False,  # It's an expense
            category_name=purchase.category_name,
            status='completed'  # Already done
        )
        db.session.add(transaction)
        saved_count += 1

    db.session.commit()

    flash(f'{saved_count} card purchase(s) saved successfully!', 'success')
    return redirect(url_for('card_purchases.list_purchases'))


@bp.route('/<int:purchase_id>')
@login_required
def detail(purchase_id):
    """Card purchase detail"""
    purchase = CardPurchase.query.get_or_404(purchase_id)

    if purchase.user_id != current_user.id:
        flash('You don\'t have access to this purchase.', 'danger')
        return redirect(url_for('card_purchases.list_purchases'))

    return render_template('card_purchases/detail.html', purchase=purchase)


@bp.route('/<int:purchase_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(purchase_id):
    """Edit a card purchase"""
    purchase = CardPurchase.query.get_or_404(purchase_id)

    if purchase.user_id != current_user.id:
        flash('You don\'t have access to this purchase.', 'danger')
        return redirect(url_for('card_purchases.list_purchases'))

    if request.method == 'POST':
        purchase.merchant_name = request.form.get('merchant_name')
        purchase.amount = float(request.form.get('amount'))

        date_str = request.form.get('purchase_date')
        time_str = request.form.get('purchase_time', '12:00')
        purchase.purchase_date = datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %H:%M')

        purchase.payment_type = request.form.get('payment_type', 'card')
        purchase.description = request.form.get('description')
        purchase.notes = request.form.get('notes')
        purchase.was_manually_edited = True

        # Update category
        category_id = request.form.get('category_id', type=int)
        if category_id:
            category = Category.query.get(category_id)
            purchase.category_id = category_id
            purchase.category_name = category.name

        # Handle uploaded receipt (optional)
        receipt_file = request.files.get('receipt_file')
        if receipt_file and receipt_file.filename:
            # Validate file
            is_valid, error_message, file_data, safe_filename = validate_upload(receipt_file)
            if not is_valid:
                flash(f'Error with receipt: {error_message}', 'warning')
            else:
                # Store file (replaces old one if exists)
                purchase.receipt_image_data = file_data
                purchase.receipt_image_name = safe_filename
                purchase.receipt_image_mime_type = receipt_file.content_type
                purchase.receipt_image_size = len(file_data)

        db.session.commit()

        # Update associated transaction
        transaction = Transaction.query.filter_by(
            source_id=purchase.id,
            source_type='card_purchase'
        ).first()

        if transaction:
            transaction.transaction_date = purchase.purchase_date.date()
            transaction.name = f'Card Purchase - {purchase.merchant_name}'
            transaction.description = purchase.description
            transaction.amount = purchase.amount
            transaction.category_name = purchase.category_name
            db.session.commit()

        flash('Purchase updated successfully.', 'success')
        return redirect(url_for('card_purchases.detail', purchase_id=purchase.id))

    # Get categories (only those for card purchases or 'all')
    categories = Category.query.filter(
        db.or_(
            Category.user_id == current_user.id,
            Category.user_id == None
        ),
        db.or_(
            Category.category_type == 'card_purchase',
            Category.category_type == 'all'
        )
    ).filter_by(is_active=True).order_by(Category.name).all()

    return render_template('card_purchases/edit.html',
                         purchase=purchase,
                         categories=categories)


@bp.route('/<int:purchase_id>/delete', methods=['POST'])
@login_required
def delete(purchase_id):
    """Delete a card purchase"""
    purchase = CardPurchase.query.get_or_404(purchase_id)

    if purchase.user_id != current_user.id:
        flash('You don\'t have access to this purchase.', 'danger')
        return redirect(url_for('card_purchases.list_purchases'))

    # Delete associated transaction
    transaction = Transaction.query.filter_by(
        source_id=purchase.id,
        source_type='card_purchase'
    ).first()

    if transaction:
        transaction.status = 'cancelled'

    purchase.is_active = False
    db.session.commit()

    flash('Purchase deleted.', 'success')
    return redirect(url_for('card_purchases.list_purchases'))


@bp.route('/<int:purchase_id>/receipt')
@login_required
def view_receipt(purchase_id):
    """Display receipt (image or PDF)"""
    purchase = CardPurchase.query.get_or_404(purchase_id)

    if purchase.user_id != current_user.id:
        flash('You don\'t have access to this purchase.', 'danger')
        return redirect(url_for('card_purchases.list_purchases'))

    if not purchase.receipt_image_data:
        flash('No receipt available.', 'warning')
        return redirect(url_for('card_purchases.detail', purchase_id=purchase.id))

    # Determine correct mimetype
    mimetype = purchase.receipt_image_mime_type or 'application/octet-stream'

    # If filename indicates PDF, ensure mimetype is correct
    if purchase.receipt_image_name and purchase.receipt_image_name.lower().endswith('.pdf'):
        mimetype = 'application/pdf'

    return Response(
        purchase.receipt_image_data,
        mimetype=mimetype,
        headers={'Content-Disposition': get_safe_content_disposition(purchase.receipt_image_name, inline=True)}
    )


@bp.route('/<int:purchase_id>/receipt/download')
@login_required
def download_receipt(purchase_id):
    """Download receipt"""
    purchase = CardPurchase.query.get_or_404(purchase_id)

    if purchase.user_id != current_user.id:
        flash('You don\'t have access to this purchase.', 'danger')
        return redirect(url_for('card_purchases.list_purchases'))

    if not purchase.receipt_image_data:
        flash('No receipt available.', 'warning')
        return redirect(url_for('card_purchases.detail', purchase_id=purchase.id))

    # Determine correct mimetype
    mimetype = purchase.receipt_image_mime_type or 'application/octet-stream'

    if purchase.receipt_image_name and purchase.receipt_image_name.lower().endswith('.pdf'):
        mimetype = 'application/pdf'

    return Response(
        purchase.receipt_image_data,
        mimetype=mimetype,
        headers={'Content-Disposition': get_safe_content_disposition(purchase.receipt_image_name, inline=False)}
    )
