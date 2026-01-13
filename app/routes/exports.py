"""
Routes pour les exports PDF et Excel (fonctionnalité Premium uniquement)
"""
from flask import Blueprint, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from functools import wraps
from app.models import Subscription, Category, Service, Credit
from app.utils.exports import (
    export_upcoming_renewals_excel, export_upcoming_renewals_pdf,
    export_category_distribution_excel, export_category_distribution_pdf,
    export_monthly_evolution_excel, export_monthly_evolution_pdf,
    export_subscriptions_excel, export_subscriptions_pdf,
    export_categories_excel, export_categories_pdf,
    export_services_excel, export_services_pdf,
    export_upcoming_credits_excel, export_upcoming_credits_pdf
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


@bp.route('/dashboard/category-distribution/<format>')
@login_required
@premium_required
def export_category_distribution(format):
    """Exporte la répartition par catégorie"""
    # Calculer la répartition
    subscriptions = Subscription.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()

    category_data = {}
    for sub in subscriptions:
        cat_name = sub.category.name if sub.category else 'Sans catégorie'
        monthly_cost = sub.amount

        # Convertir en coût mensuel selon le cycle
        if sub.billing_cycle == 'yearly':
            monthly_cost = sub.amount / 12
        elif sub.billing_cycle == 'quarterly':
            monthly_cost = sub.amount / 3
        elif sub.billing_cycle == 'weekly':
            monthly_cost = sub.amount * 4

        if cat_name not in category_data:
            category_data[cat_name] = {'name': cat_name, 'count': 0, 'amount': 0}

        category_data[cat_name]['count'] += 1
        category_data[cat_name]['amount'] += monthly_cost

    category_list = sorted(category_data.values(), key=lambda x: x['amount'], reverse=True)

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


@bp.route('/dashboard/monthly-evolution/<format>')
@login_required
@premium_required
def export_monthly_evolution(format):
    """Exporte l'évolution des dépenses mensuelles"""
    # Calculer l'évolution sur les 12 derniers mois
    subscriptions = Subscription.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()

    monthly_data = []
    now = datetime.now()

    for i in range(11, -1, -1):
        month_date = now - timedelta(days=30*i)
        month_name = month_date.strftime('%B %Y')

        total = 0
        for sub in subscriptions:
            if sub.start_date <= month_date.date():
                monthly_cost = sub.amount

                # Convertir en coût mensuel selon le cycle
                if sub.billing_cycle == 'yearly':
                    monthly_cost = sub.amount / 12
                elif sub.billing_cycle == 'quarterly':
                    monthly_cost = sub.amount / 3
                elif sub.billing_cycle == 'weekly':
                    monthly_cost = sub.amount * 4

                total += monthly_cost

        monthly_data.append({'month': month_name, 'amount': total})

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
