"""
Routes pour les exports PDF et Excel (fonctionnalité Premium uniquement)
"""
from flask import Blueprint, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from functools import wraps
from sqlalchemy import func
from app import db
from app.models import Subscription, Category, Service, Credit, Revenue, Transaction
from app.utils.exports import (
    export_upcoming_renewals_excel, export_upcoming_renewals_pdf,
    export_category_distribution_excel, export_category_distribution_pdf,
    export_monthly_evolution_excel, export_monthly_evolution_pdf,
    export_subscriptions_excel, export_subscriptions_pdf,
    export_categories_excel, export_categories_pdf,
    export_services_excel, export_services_pdf,
    export_upcoming_credits_excel, export_upcoming_credits_pdf,
    export_upcoming_revenues_excel, export_upcoming_revenues_pdf,
    export_revenue_distribution_excel, export_revenue_distribution_pdf,
    export_unpointed_checks_excel, export_unpointed_checks_pdf
)

bp = Blueprint('exports', __name__, url_prefix='/exports')


def premium_required(f):
    """Décorateur pour vérifier que l'utilisateur est Premium"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_premium():
            flash('Cette fonctionnalité est réservée aux utilisateurs Premium.', 'warning')
            return redirect(url_for('main.pricing'))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/dashboard/upcoming-renewals/<format>')
@login_required
@premium_required
def export_upcoming_renewals(format):
    """Exporte les prochains renouvellements"""
    # Récupérer les 30 prochains jours
    upcoming_renewals = Subscription.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).filter(
        Subscription.next_billing_date <= datetime.now().date() + timedelta(days=30)
    ).order_by(Subscription.next_billing_date).all()

    if format == 'excel':
        output = export_upcoming_renewals_excel(upcoming_renewals, current_user)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'abonnements_prochains_renouvellements_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    elif format == 'pdf':
        output = export_upcoming_renewals_pdf(upcoming_renewals, current_user)
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'abonnements_prochains_renouvellements_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
    else:
        flash('Format non supporté', 'danger')
        return redirect(url_for('main.dashboard'))


@bp.route('/dashboard/upcoming-credits/<format>')
@login_required
@premium_required
def export_upcoming_credits(format):
    """Exporte les prochains prélèvements pour les crédits"""
    # Récupérer tous les crédits actifs
    upcoming_credits = Credit.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).order_by(Credit.next_payment_date).all()

    if format == 'excel':
        output = export_upcoming_credits_excel(upcoming_credits, current_user)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'credits_prochains_prelevements_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    elif format == 'pdf':
        output = export_upcoming_credits_pdf(upcoming_credits, current_user)
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'credits_prochains_prelevements_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
    else:
        flash('Format non supporté', 'danger')
        return redirect(url_for('main.dashboard'))


@bp.route('/dashboard/upcoming-revenues/<format>')
@login_required
@premium_required
def export_upcoming_revenues(format):
    """Exporte les prochains versements pour les revenus"""
    # Récupérer tous les revenus actifs
    upcoming_revenues = Revenue.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).order_by(Revenue.next_payment_date).all()

    if format == 'excel':
        output = export_upcoming_revenues_excel(upcoming_revenues, current_user)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'revenus_prochains_versements_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    elif format == 'pdf':
        output = export_upcoming_revenues_pdf(upcoming_revenues, current_user)
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'revenus_prochains_versements_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
    else:
        flash('Format non supporté', 'danger')
        return redirect(url_for('main.dashboard'))


@bp.route('/dashboard/unpointed-checks/<format>')
@login_required
@premium_required
def export_unpointed_checks(format):
    """Exporte les chèques non débités (non pointés)"""
    # Récupérer les chèques non pointés
    unpointed_checks = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == 'check',
        Transaction.status == 'completed',
        Transaction.is_pointed == False
    ).order_by(Transaction.transaction_date.desc()).all()

    if format == 'excel':
        output = export_unpointed_checks_excel(unpointed_checks, current_user)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'cheques_non_debites_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    elif format == 'pdf':
        output = export_unpointed_checks_pdf(unpointed_checks, current_user)
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'cheques_non_debites_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
    else:
        flash('Format non supporté', 'danger')
        return redirect(url_for('main.dashboard'))


@bp.route('/dashboard/category-distribution/<format>')
@login_required
@premium_required
def export_category_distribution(format):
    """Exporte la répartition des abonnements et crédits par catégorie"""
    # Utiliser la même logique que le dashboard
    # Répartition par catégorie (abonnements + crédits) - même requête que le dashboard
    category_stats = db.session.query(
        Category.name,
        Category.color,
        func.count(Subscription.id).label('subscription_count'),
        func.sum(Subscription.amount).label('subscription_total'),
        func.count(Credit.id).label('credit_count'),
        func.sum(Credit.amount).label('credit_total'),
        (func.coalesce(func.sum(Subscription.amount), 0) + func.coalesce(func.sum(Credit.amount), 0)).label('total')
    ).outerjoin(Subscription,
        (Subscription.category_id == Category.id) &
        (Subscription.user_id == current_user.id) &
        (Subscription.is_active == True)
    ).outerjoin(Credit,
        (Credit.category_id == Category.id) &
        (Credit.user_id == current_user.id) &
        (Credit.is_active == True)
    ).filter(
        (Subscription.id != None) | (Credit.id != None)
    ).group_by(Category.id).all()

    # Convertir en liste de dictionnaires
    category_data = []
    for stat in category_stats:
        category_data.append({
            'name': stat.name,
            'color': stat.color,
            'count': (stat.subscription_count or 0) + (stat.credit_count or 0),
            'amount': stat.total
        })

    # Calculer le total des crédits actifs pour la catégorie "Crédits"
    credits = Credit.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()

    total_credits = sum(
        credit.amount if credit.billing_cycle == 'monthly' else
        credit.amount / 3 if credit.billing_cycle == 'quarterly' else
        credit.amount / 12 if credit.billing_cycle == 'yearly' else 0
        for credit in credits
    )

    # Ajouter la catégorie "Crédits" si elle a un montant
    if total_credits > 0:
        category_data.append({
            'name': 'Crédits',
            'color': '#ffc107',
            'count': len(credits),
            'amount': total_credits
        })

    category_list = sorted(category_data, key=lambda x: x['amount'], reverse=True)

    if format == 'excel':
        output = export_category_distribution_excel(category_list, current_user)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'repartition_categories_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    elif format == 'pdf':
        output = export_category_distribution_pdf(category_list, current_user)
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'repartition_categories_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
    else:
        flash('Format non supporté', 'danger')
        return redirect(url_for('main.dashboard'))


@bp.route('/dashboard/revenue-distribution/<format>')
@login_required
@premium_required
def export_revenue_distribution(format):
    """Exporte la répartition des versements (revenus)"""
    # Calculer la répartition par employeur
    revenues = Revenue.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()

    revenue_data = {}
    for revenue in revenues:
        if revenue.employer:
            employer_name = revenue.employer.name
        else:
            employer_name = 'Autres revenus'

        monthly_amount = revenue.amount

        # Convertir en montant mensuel selon le cycle
        if revenue.billing_cycle == 'yearly':
            monthly_amount = revenue.amount / 12
        elif revenue.billing_cycle == 'quarterly':
            monthly_amount = revenue.amount / 3

        if employer_name not in revenue_data:
            revenue_data[employer_name] = {'name': employer_name, 'total': 0}

        revenue_data[employer_name]['total'] += monthly_amount

    revenue_list = sorted(revenue_data.values(), key=lambda x: x['total'], reverse=True)

    if format == 'excel':
        output = export_revenue_distribution_excel(revenue_list, current_user)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'repartition_revenus_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    elif format == 'pdf':
        output = export_revenue_distribution_pdf(revenue_list, current_user)
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'repartition_revenus_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
    else:
        flash('Format non supporté', 'danger')
        return redirect(url_for('main.dashboard'))


@bp.route('/dashboard/monthly-evolution/<format>')
@login_required
@premium_required
def export_monthly_evolution(format):
    """Exporte l'évolution des revenus et dépenses mensuelles"""
    # Récupérer tous les éléments actifs
    subscriptions = Subscription.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()

    credits = Credit.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()

    revenues = Revenue.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()

    monthly_data = []
    now = datetime.now()

    for i in range(11, -1, -1):
        month_date = now - timedelta(days=30*i)
        month_name = month_date.strftime('%B %Y')

        # Calculer les abonnements
        sub_total = 0
        for sub in subscriptions:
            if sub.start_date <= month_date.date():
                monthly_cost = sub.amount
                if sub.billing_cycle == 'yearly':
                    monthly_cost = sub.amount / 12
                elif sub.billing_cycle == 'quarterly':
                    monthly_cost = sub.amount / 3
                elif sub.billing_cycle == 'weekly':
                    monthly_cost = sub.amount * 4
                sub_total += monthly_cost

        # Calculer les crédits
        credit_total = 0
        for credit in credits:
            if credit.start_date <= month_date.date() and (credit.end_date is None or credit.end_date >= month_date.date()):
                monthly_cost = credit.amount
                if credit.billing_cycle == 'yearly':
                    monthly_cost = credit.amount / 12
                elif credit.billing_cycle == 'quarterly':
                    monthly_cost = credit.amount / 3
                credit_total += monthly_cost

        # Calculer les revenus
        revenue_total = 0
        for revenue in revenues:
            if revenue.start_date <= month_date.date():
                monthly_amount = revenue.amount
                if revenue.billing_cycle == 'yearly':
                    monthly_amount = revenue.amount / 12
                elif revenue.billing_cycle == 'quarterly':
                    monthly_amount = revenue.amount / 3
                revenue_total += monthly_amount

        monthly_data.append({
            'month': month_name,
            'subscriptions': sub_total,
            'credits': credit_total,
            'revenues': revenue_total
        })

    if format == 'excel':
        output = export_monthly_evolution_excel(monthly_data, current_user)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'evolution_mensuelle_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    elif format == 'pdf':
        output = export_monthly_evolution_pdf(monthly_data, current_user)
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'evolution_mensuelle_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
    else:
        flash('Format non supporté', 'danger')
        return redirect(url_for('main.dashboard'))


@bp.route('/subscriptions/<format>')
@login_required
@premium_required
def export_subscriptions(format):
    """Exporte la liste des abonnements"""
    subscriptions = Subscription.query.filter_by(user_id=current_user.id).order_by(Subscription.created_at.desc()).all()

    if format == 'excel':
        output = export_subscriptions_excel(subscriptions, current_user)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'mes_abonnements_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    elif format == 'pdf':
        output = export_subscriptions_pdf(subscriptions, current_user)
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'mes_abonnements_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
    else:
        flash('Format non supporté', 'danger')
        return redirect(url_for('subscriptions.list'))


@bp.route('/categories/<format>')
@login_required
@premium_required
def export_categories(format):
    """Exporte la liste des catégories"""
    # Catégories personnalisées de l'utilisateur
    custom_categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    # Catégories globales
    global_categories = Category.query.filter_by(user_id=None, is_active=True).order_by(Category.name).all()

    all_categories = custom_categories + global_categories

    if format == 'excel':
        output = export_categories_excel(all_categories, current_user)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'mes_categories_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    elif format == 'pdf':
        output = export_categories_pdf(all_categories, current_user)
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'mes_categories_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
    else:
        flash('Format non supporté', 'danger')
        return redirect(url_for('categories.list'))


@bp.route('/services/<format>')
@login_required
@premium_required
def export_services(format):
    """Exporte la liste des services"""
    # Services personnalisés de l'utilisateur
    custom_services = Service.query.filter_by(user_id=current_user.id).order_by(Service.name).all()
    # Services globaux non masqués
    global_services = Service.query.filter_by(user_id=None, is_active=True).filter(
        ~Service.hidden_by_users.any(id=current_user.id)
    ).order_by(Service.name).all()

    all_services = custom_services + global_services

    if format == 'excel':
        output = export_services_excel(all_services, current_user)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'mes_services_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    elif format == 'pdf':
        output = export_services_pdf(all_services, current_user)
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'mes_services_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
    else:
        flash('Format non supporté', 'danger')
        return redirect(url_for('services.list'))
