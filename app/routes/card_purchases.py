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
    """Liste tous les achats CB de l'utilisateur"""
    page = request.args.get('page', 1, type=int)
    filter_category = request.args.get('category', None, type=int)

    # Définir les filtres par défaut au mois et année en cours si pas de paramètre dans l'URL
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Si aucun paramètre de mois/année n'est présent, utiliser le mois/année en cours
    # Sinon, utiliser ce qui est fourni (peut être None si l'utilisateur choisit "Tous")
    if 'month' not in request.args and 'year' not in request.args:
        filter_month = current_month
        filter_year = current_year
    else:
        filter_month = request.args.get('month', type=int) if request.args.get('month') else None
        filter_year = request.args.get('year', type=int) if request.args.get('year') else None

    query = current_user.card_purchases.filter_by(is_active=True)

    # Filtres
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

    # Récupérer les catégories pour le filtre (seulement celles pour achats CB ou 'all')
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
    """Ajouter un achat CB manuellement (mode par défaut)"""

    # Récupérer les catégories (seulement celles pour achats CB ou 'all')
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
            # Récupérer les données du formulaire
            merchant_name = request.form.get('merchant_name')
            amount = float(request.form.get('amount'))
            purchase_date = request.form.get('purchase_date')
            purchase_time = request.form.get('purchase_time', '12:00')
            category_id = request.form.get('category_id', type=int)
            description = request.form.get('description', '')

            # Créer l'achat CB
            purchase = CardPurchase(
                user_id=current_user.id,
                purchase_date=datetime.strptime(f'{purchase_date} {purchase_time}', '%Y-%m-%d %H:%M'),
                merchant_name=merchant_name,
                amount=amount,
                currency='EUR',
                description=description,
                ocr_confidence=0,  # Pas d'OCR
                was_manually_edited=True,
                entry_method='manual',  # Saisie manuelle
            )

            # Associer une catégorie si sélectionnée
            if category_id:
                category = Category.query.get(category_id)
                if category:
                    purchase.category_id = category_id
                    purchase.category_name = category.name

            # Gérer le reçu uploadé (optionnel)
            receipt_file = request.files.get('receipt_file')
            if receipt_file and receipt_file.filename:
                # Valider le fichier
                is_valid, error_message, file_data, safe_filename = validate_upload(receipt_file)
                if not is_valid:
                    flash(f'Erreur avec le reçu : {error_message}', 'warning')
                else:
                    # Stocker le fichier
                    purchase.receipt_image_data = file_data
                    purchase.receipt_image_name = safe_filename
                    purchase.receipt_image_mime_type = receipt_file.content_type
                    purchase.receipt_image_size = len(file_data)

            db.session.add(purchase)
            db.session.flush()

            # Créer la transaction dans la balance
            transaction = Transaction(
                user_id=current_user.id,
                transaction_date=purchase.purchase_date.date(),
                transaction_type='card_purchase',
                source_id=purchase.id,
                source_type='card_purchase',
                name=f'Achat CB - {purchase.merchant_name}',
                description=purchase.description,
                amount=purchase.amount,
                currency='EUR',
                is_positive=False,
                category_name=purchase.category_name,
                status='completed'
            )
            db.session.add(transaction)
            db.session.commit()

            flash('Achat CB ajouté avec succès !', 'success')
            return redirect(url_for('card_purchases.list_purchases'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'ajout : {str(e)}', 'danger')

    # GET : Afficher le formulaire
    return render_template('card_purchases/add_manual.html',
                         categories=categories,
                         today=datetime.now().strftime('%Y-%m-%d'))


@bp.route('/upload', methods=['GET', 'POST'])
@login_required
@limiter.limit("50 per hour")
def upload_receipts():
    """Upload multiple avec traitement OCR et grille de validation"""

    if request.method == 'POST':
        # Récupérer tous les fichiers uploadés
        files = request.files.getlist('receipts')

        if not files or len(files) == 0:
            flash('Aucun fichier sélectionné.', 'warning')
            return redirect(url_for('card_purchases.upload_receipts'))

        # Limiter à 10 fichiers par upload
        if len(files) > 10:
            flash('Maximum 10 fichiers par upload.', 'warning')
            return redirect(url_for('card_purchases.upload_receipts'))

        processed_receipts = []

        # Traiter chaque fichier
        for file in files:
            if not file or not file.filename:
                continue

            # Valider le fichier
            success, error, file_data, safe_filename = validate_upload(file)

            if not success:
                flash(f'Erreur avec {file.filename}: {error}', 'danger')
                continue

            # Traiter l'OCR
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Traitement OCR de {safe_filename} ({file.content_type}, {len(file_data)} bytes)")

                ocr_data = process_receipt_ocr(file_data)

                logger.info(f"OCR réussi: {ocr_data['merchant_name']}, {ocr_data['amount']}€, confiance={ocr_data['ocr_confidence']:.1f}%")

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
                logger.error(f'Erreur OCR avec {safe_filename}: {type(e).__name__}: {str(e)}')
                import traceback
                logger.error(traceback.format_exc())

                # Message d'erreur plus informatif pour l'utilisateur
                if 'PDF' in str(e) or safe_filename.lower().endswith('.pdf'):
                    flash(f'Erreur lors de la conversion du PDF "{file.filename}". Assurez-vous que le PDF est lisible et contient du texte.', 'danger')
                else:
                    flash(f'Erreur OCR avec "{file.filename}": {str(e)}', 'danger')
                continue

        if not processed_receipts:
            flash('Aucun reçu valide n\'a pu être traité.', 'danger')
            return redirect(url_for('card_purchases.upload_receipts'))

        # Récupérer les catégories pour le formulaire (seulement celles pour achats CB ou 'all')
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

    # GET : Afficher le formulaire d'upload
    return render_template('card_purchases/upload.html')


@bp.route('/validate', methods=['POST'])
@login_required
def validate_purchases():
    """Valide et enregistre les achats après modification par l'utilisateur"""

    # Récupérer les données du formulaire
    purchases_data = request.form.get('purchases_json')

    if not purchases_data:
        flash('Aucune donnée à enregistrer.', 'danger')
        return redirect(url_for('card_purchases.upload_receipts'))

    try:
        purchases = json.loads(purchases_data)
    except json.JSONDecodeError:
        flash('Erreur lors du traitement des données.', 'danger')
        return redirect(url_for('card_purchases.upload_receipts'))

    saved_count = 0

    for purchase_data in purchases:
        # Vérifier si l'utilisateur veut garder cet achat
        if not purchase_data.get('keep', True):
            continue

        # Décoder l'image
        try:
            receipt_data = base64.b64decode(purchase_data['file_data_base64'])
        except Exception:
            receipt_data = None

        # Créer l'achat CB
        purchase = CardPurchase(
            user_id=current_user.id,
            purchase_date=datetime.strptime(
                f"{purchase_data['purchase_date']} {purchase_data.get('purchase_time', '12:00')}",
                '%Y-%m-%d %H:%M'
            ),
            merchant_name=purchase_data['merchant_name'],
            amount=float(purchase_data['amount']),
            currency='EUR',
            category_name=purchase_data.get('category_name'),
            description=purchase_data.get('description', ''),
            ocr_confidence=float(purchase_data.get('ocr_confidence', 0)),
            was_manually_edited=purchase_data.get('was_edited', False),
            entry_method='ocr',  # Saisie par OCR
            receipt_image_data=receipt_data,
            receipt_image_name=purchase_data.get('file_name'),
            receipt_image_mime_type=purchase_data.get('file_mime_type'),
            receipt_image_size=purchase_data.get('file_size')
        )

        # Associer une catégorie si possible
        if purchase_data.get('category_id'):
            category_id = int(purchase_data['category_id'])
            category = Category.query.get(category_id)
            if category:
                purchase.category_id = category_id
                purchase.category_name = category.name

        db.session.add(purchase)
        db.session.flush()

        # Créer la transaction dans la balance
        transaction = Transaction(
            user_id=current_user.id,
            transaction_date=purchase.purchase_date.date(),
            transaction_type='card_purchase',
            source_id=purchase.id,
            source_type='card_purchase',
            name=f'Achat CB - {purchase.merchant_name}',
            description=purchase.description,
            amount=purchase.amount,
            currency='EUR',
            is_positive=False,  # C'est une dépense
            category_name=purchase.category_name,
            status='completed'  # Déjà effectué
        )
        db.session.add(transaction)
        saved_count += 1

    db.session.commit()

    flash(f'{saved_count} achat(s) CB enregistré(s) avec succès !', 'success')
    return redirect(url_for('card_purchases.list_purchases'))


@bp.route('/<int:purchase_id>')
@login_required
def detail(purchase_id):
    """Détail d'un achat CB"""
    purchase = CardPurchase.query.get_or_404(purchase_id)

    if purchase.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cet achat.', 'danger')
        return redirect(url_for('card_purchases.list_purchases'))

    return render_template('card_purchases/detail.html', purchase=purchase)


@bp.route('/<int:purchase_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(purchase_id):
    """Modifier un achat CB"""
    purchase = CardPurchase.query.get_or_404(purchase_id)

    if purchase.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cet achat.', 'danger')
        return redirect(url_for('card_purchases.list_purchases'))

    if request.method == 'POST':
        purchase.merchant_name = request.form.get('merchant_name')
        purchase.amount = float(request.form.get('amount'))

        date_str = request.form.get('purchase_date')
        time_str = request.form.get('purchase_time', '12:00')
        purchase.purchase_date = datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %H:%M')

        purchase.description = request.form.get('description')
        purchase.notes = request.form.get('notes')
        purchase.was_manually_edited = True

        # Mettre à jour la catégorie
        category_id = request.form.get('category_id', type=int)
        if category_id:
            category = Category.query.get(category_id)
            purchase.category_id = category_id
            purchase.category_name = category.name

        # Gérer le reçu uploadé (optionnel)
        receipt_file = request.files.get('receipt_file')
        if receipt_file and receipt_file.filename:
            # Valider le fichier
            is_valid, error_message, file_data, safe_filename = validate_upload(receipt_file)
            if not is_valid:
                flash(f'Erreur avec le reçu : {error_message}', 'warning')
            else:
                # Stocker le fichier (remplace l'ancien s'il existe)
                purchase.receipt_image_data = file_data
                purchase.receipt_image_name = safe_filename
                purchase.receipt_image_mime_type = receipt_file.content_type
                purchase.receipt_image_size = len(file_data)

        db.session.commit()

        # Mettre à jour la transaction associée
        transaction = Transaction.query.filter_by(
            source_id=purchase.id,
            source_type='card_purchase'
        ).first()

        if transaction:
            transaction.transaction_date = purchase.purchase_date.date()
            transaction.name = f'Achat CB - {purchase.merchant_name}'
            transaction.description = purchase.description
            transaction.amount = purchase.amount
            transaction.category_name = purchase.category_name
            db.session.commit()

        flash('L\'achat a été modifié avec succès.', 'success')
        return redirect(url_for('card_purchases.detail', purchase_id=purchase.id))

    # Récupérer les catégories (seulement celles pour achats CB ou 'all')
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
    """Supprimer un achat CB"""
    purchase = CardPurchase.query.get_or_404(purchase_id)

    if purchase.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cet achat.', 'danger')
        return redirect(url_for('card_purchases.list_purchases'))

    # Supprimer la transaction associée
    transaction = Transaction.query.filter_by(
        source_id=purchase.id,
        source_type='card_purchase'
    ).first()

    if transaction:
        transaction.status = 'cancelled'

    purchase.is_active = False
    db.session.commit()

    flash('L\'achat a été supprimé.', 'success')
    return redirect(url_for('card_purchases.list_purchases'))


@bp.route('/<int:purchase_id>/receipt')
@login_required
def view_receipt(purchase_id):
    """Afficher le reçu (image ou PDF)"""
    purchase = CardPurchase.query.get_or_404(purchase_id)

    if purchase.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cet achat.', 'danger')
        return redirect(url_for('card_purchases.list_purchases'))

    if not purchase.receipt_image_data:
        flash('Aucun reçu disponible.', 'warning')
        return redirect(url_for('card_purchases.detail', purchase_id=purchase.id))

    # Déterminer le mimetype correct
    mimetype = purchase.receipt_image_mime_type or 'application/octet-stream'

    # Si le nom de fichier indique un PDF, s'assurer que le mimetype est correct
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
    """Télécharger le reçu"""
    purchase = CardPurchase.query.get_or_404(purchase_id)

    if purchase.user_id != current_user.id:
        flash('Vous n\'avez pas accès à cet achat.', 'danger')
        return redirect(url_for('card_purchases.list_purchases'))

    if not purchase.receipt_image_data:
        flash('Aucun reçu disponible.', 'warning')
        return redirect(url_for('card_purchases.detail', purchase_id=purchase.id))

    # Déterminer le mimetype correct
    mimetype = purchase.receipt_image_mime_type or 'application/octet-stream'

    if purchase.receipt_image_name and purchase.receipt_image_name.lower().endswith('.pdf'):
        mimetype = 'application/pdf'

    return Response(
        purchase.receipt_image_data,
        mimetype=mimetype,
        headers={'Content-Disposition': get_safe_content_disposition(purchase.receipt_image_name, inline=False)}
    )
