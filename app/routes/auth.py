from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, current_app
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from app import db
from app.models import User, Plan
from datetime import datetime
import os

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)

        user = User.query.filter_by(email=email).first()

        if user is None or not user.check_password(password):
            flash('Email ou mot de passe incorrect.', 'danger')
            return redirect(url_for('auth.login'))

        if not user.is_active:
            flash('Votre compte a été désactivé. Veuillez contacter le support.', 'warning')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)

        # Vérifier s'il y a un plan premium en attente (après inscription)
        if 'pending_premium_plan' in session:
            pending_plan = session.pop('pending_premium_plan')
            flash(f'Bienvenue {user.first_name or user.email} ! Finalisez maintenant votre paiement pour activer votre plan Premium.', 'success')
            return redirect(url_for('main.checkout_redirect', plan=pending_plan))

        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('main.dashboard')

        flash(f'Bienvenue {user.first_name or user.email} !', 'success')
        return redirect(next_page)

    return render_template('auth/login.html')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        default_currency = request.form.get('default_currency', 'EUR')
        country = request.form.get('country', 'FR')

        # Vérifier si l'utilisateur s'inscrit pour un plan Premium
        plan_param = request.args.get('plan', '')
        is_premium_signup = plan_param in ['premium', 'premium-annual']

        if password != password_confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(email=email).first():
            flash('Cette adresse email est déjà utilisée.', 'danger')
            return redirect(url_for('auth.register'))

        # Créer l'utilisateur avec le plan gratuit par défaut
        free_plan = Plan.query.filter_by(name='Free').first()
        if not free_plan:
            # Créer le plan gratuit s'il n'existe pas
            free_plan = Plan(
                name='Free',
                price=0.0,
                max_subscriptions=5,
                description='Plan gratuit - Maximum 5 abonnements',
                features=['5 abonnements maximum', 'Catégories', 'Statistiques', 'Notifications']
            )
            db.session.add(free_plan)
            db.session.commit()

        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            default_currency=default_currency,
            plan=free_plan
        )
        user.set_password(password)
        user.set_country(country)  # Définit le pays et le fuseau horaire automatiquement

        db.session.add(user)
        db.session.commit()

        # Envoyer l'email de vérification
        from app.utils.email import send_verification_email, send_welcome_email, send_new_subscription_notification
        send_verification_email(user)

        # Envoyer l'email de bienvenue et la notification uniquement si ce n'est pas une inscription Premium
        # Pour Premium, ces emails seront envoyés après le paiement réussi
        if not is_premium_signup:
            # Envoyer l'email de bienvenue avec récapitulatif du plan
            send_welcome_email(user)

            # Envoyer la notification à l'équipe
            send_new_subscription_notification(user)

        db.session.commit()

        # Message de confirmation adapté selon le type d'inscription
        if is_premium_signup:
            # Stocker le plan choisi dans la session pour rediriger après connexion
            session['pending_premium_plan'] = 'yearly' if plan_param == 'premium-annual' else 'monthly'
            flash('Votre compte a été créé avec succès ! Un email de confirmation a été envoyé à votre adresse. Vous pourrez finaliser votre paiement Premium après avoir vérifié votre email.', 'success')
        else:
            flash('Votre compte a été créé avec succès ! Un email de confirmation a été envoyé à votre adresse.', 'success')

        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@bp.route('/api/register', methods=['POST'])
def api_register():
    """API d'inscription pour les modales (retourne JSON)"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        country = data.get('country', 'FR')
        plan_type = data.get('plan_type', '')  # 'monthly' ou 'yearly'

        # Validation
        if not all([email, password, first_name, last_name, country]):
            return jsonify({'error': 'Tous les champs sont requis'}), 400

        if len(password) < 6:
            return jsonify({'error': 'Le mot de passe doit contenir au moins 6 caractères'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Cette adresse email est déjà utilisée'}), 400

        # Créer l'utilisateur avec le plan gratuit par défaut
        free_plan = Plan.query.filter_by(name='Free').first()
        if not free_plan:
            free_plan = Plan(
                name='Free',
                price=0.0,
                max_subscriptions=5,
                description='Plan gratuit - Maximum 5 abonnements',
                features=['5 abonnements maximum', 'Catégories', 'Statistiques', 'Notifications']
            )
            db.session.add(free_plan)
            db.session.commit()

        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            default_currency='EUR',
            plan=free_plan
        )
        user.set_password(password)
        user.set_country(country)

        db.session.add(user)
        db.session.commit()

        # Envoyer l'email de vérification
        from app.utils.email import send_verification_email
        send_verification_email(user)

        # Connecter automatiquement l'utilisateur
        login_user(user)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Compte créé avec succès',
            'user_id': user.id,
            'plan_type': plan_type
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Erreur lors de l\'inscription API: {str(e)}')
        return jsonify({'error': 'Une erreur est survenue lors de l\'inscription'}), 500


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté avec succès.', 'info')
    return redirect(url_for('main.index'))


@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.default_currency = request.form.get('default_currency', 'EUR')

        # Mettre à jour le pays et le fuseau horaire
        country = request.form.get('country')
        if country:
            current_user.set_country(country)

        # Changement de mot de passe
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        new_password_confirm = request.form.get('new_password_confirm')

        if current_password and new_password:
            if not current_user.check_password(current_password):
                flash('Mot de passe actuel incorrect.', 'danger')
                return redirect(url_for('auth.profile'))

            if new_password != new_password_confirm:
                flash('Les nouveaux mots de passe ne correspondent pas.', 'danger')
                return redirect(url_for('auth.profile'))

            current_user.set_password(new_password)
            flash('Votre mot de passe a été mis à jour.', 'success')

        db.session.commit()
        flash('Votre profil a été mis à jour avec succès.', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/profile.html')


@bp.route('/verify-email/<token>')
def verify_email(token):
    """Vérifie l'email de l'utilisateur via le token"""
    user = User.query.filter_by(email_verification_token=token).first()

    if not user:
        flash('Le lien de vérification est invalide ou a expiré.', 'danger')
        return redirect(url_for('main.index'))

    if user.email_verified:
        flash('Votre email a déjà été vérifié.', 'info')
        return redirect(url_for('main.dashboard') if current_user.is_authenticated else url_for('auth.login'))

    user.verify_email()
    db.session.commit()

    flash('Votre adresse email a été confirmée avec succès ! Vous pouvez maintenant profiter pleinement de Budgee Family.', 'success')

    if not current_user.is_authenticated:
        login_user(user)

    return redirect(url_for('main.dashboard'))


@bp.route('/resend-verification')
@login_required
def resend_verification():
    """Renvoie un email de vérification"""
    if current_user.email_verified:
        flash('Votre email est déjà vérifié.', 'info')
        return redirect(url_for('main.dashboard'))

    from app.utils.email import send_resend_verification_email

    if send_resend_verification_email(current_user):
        db.session.commit()
        flash('Un nouvel email de vérification a été envoyé à votre adresse.', 'success')
    else:
        flash('Erreur lors de l\'envoi de l\'email. Veuillez réessayer plus tard.', 'danger')

    return redirect(url_for('main.dashboard'))


@bp.route('/downgrade-to-free', methods=['POST'])
@login_required
def downgrade_to_free():
    """Rétrograde immédiatement l'utilisateur vers le plan gratuit"""
    if not current_user.plan or current_user.plan.name == 'Free':
        flash('Vous êtes déjà sur le plan gratuit.', 'info')
        return redirect(url_for('auth.profile'))

    # Récupérer le plan gratuit
    free_plan = Plan.query.filter_by(name='Free').first()
    if not free_plan:
        flash('Erreur: Le plan gratuit n\'existe pas.', 'danger')
        return redirect(url_for('auth.profile'))

    # Sauvegarder le nom de l'ancien plan pour le message et l'email
    old_plan_name = current_user.plan.name

    # Rétrograder immédiatement
    current_user.plan = free_plan

    # Créer une notification
    from app.models import Notification
    notification = Notification(
        user_id=current_user.id,
        type='downgrade',
        title='Rétrogradation confirmée',
        message=f'Vous avez été rétrogradé du plan {old_plan_name} vers le plan gratuit.'
    )
    db.session.add(notification)
    db.session.commit()

    # Envoyer l'email de confirmation
    from app.utils.email import send_plan_downgrade_email
    send_plan_downgrade_email(current_user, old_plan_name)

    flash(f'Vous avez été rétrogradé du plan {old_plan_name} vers le plan gratuit avec succès. Un email de confirmation vous a été envoyé.', 'success')
    return redirect(url_for('auth.profile'))
