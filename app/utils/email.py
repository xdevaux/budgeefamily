from flask import url_for, render_template_string
from flask_mail import Message, Mail
from flask_babel import gettext as _
from app import mail
import os
import stripe
from datetime import datetime

def send_verification_email(user):
    """Envoie un email de vérification à l'utilisateur"""
    token = user.generate_verification_token()
    verification_url = url_for('auth.verify_email', token=token, _external=True)
    lang = user.language or 'fr'

    # Contenu selon la langue
    if lang == 'en':
        subject = 'Welcome to Budgee Family - Confirm your email'
        greeting = user.first_name or 'dear user'
        title = 'Welcome to Budgee Family!'
        intro = f'Hello {greeting},'
        thank_you = 'Thank you for signing up for <strong>Budgee Family</strong>, your intelligent subscription manager!'
        instruction = 'To start using all our features, please confirm your email address by clicking the button below:'
        button_text = 'Confirm my email address'
        ignore_text = 'If you did not create an account on Budgee Family, you can ignore this email.'
        closing = 'See you soon,<br>The Budgee Family team'
        footer_text = 'This email was sent by Budgee Family'
        link_text = 'If the button doesn\'t work, copy this link into your browser:'
    else:
        subject = 'Bienvenue sur Budgee Family - Confirmez votre email'
        greeting = user.first_name or 'cher utilisateur'
        title = 'Bienvenue sur Budgee Family !'
        intro = f'Bonjour {greeting},'
        thank_you = 'Merci de vous être inscrit sur <strong>Budgee Family</strong>, votre gestionnaire d\'abonnements intelligent !'
        instruction = 'Pour commencer à utiliser toutes nos fonctionnalités, veuillez confirmer votre adresse email en cliquant sur le bouton ci-dessous :'
        button_text = 'Confirmer mon adresse email'
        ignore_text = 'Si vous n\'avez pas créé de compte sur Budgee Family, vous pouvez ignorer cet email.'
        closing = 'À bientôt,<br>L\'équipe Budgee Family'
        footer_text = 'Cet email a été envoyé par Budgee Family'
        link_text = 'Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :'

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 10px 10px 0 0;
            }}
            .content {{
                background: #f9f9f9;
                padding: 30px;
                border-radius: 0 0 10px 10px;
            }}
            .button {{
                display: inline-block;
                padding: 12px 30px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                margin-top: 20px;
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="{url_for('static', filename='uploads/logos/budgee_family_logo_trsp.png', _external=True)}" alt="Budgee Family" width="120" style="display: block; margin: 0 auto 20px auto;">
                <h1>{title}</h1>
            </div>
            <div class="content">
                <p>{intro}</p>
                <p>{thank_you}</p>
                <p>{instruction}</p>
                <div style="text-align: center;">
                    <a href="{verification_url}" class="button">{button_text}</a>
                </div>
                <p>{ignore_text}</p>
                <p>{closing}</p>
            </div>
            <div class="footer">
                <p>{footer_text}</p>
                <p>{link_text}<br>{verification_url}</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    {title}

    {intro}

    {thank_you.replace('<strong>', '').replace('</strong>', '')}

    {instruction}
    {verification_url}

    {ignore_text}

    {closing.replace('<br>', '')}
    """

    msg = Message(
        subject=subject,
        sender=os.getenv('MAIL_DEFAULT_SENDER', 'noreply@budgeefamily.com'),
        recipients=[user.email],
        body=text_body,
        html=html_body
    )

    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email : {e}")
        return False


def send_resend_verification_email(user):
    """Renvoie un email de vérification"""
    return send_verification_email(user)


def send_plan_downgrade_email(user, old_plan_name):
    """Envoie un email de confirmation de rétrogradation vers le plan gratuit"""
    lang = user.language or 'fr'

    if lang == 'en':
        subject = 'Downgrade confirmed - Budgee Family'
        title = 'Downgrade confirmed'
        greeting = f'Hello {user.first_name or user.email},'
        confirmation = f'We confirm that your account has been downgraded from <strong>{old_plan_name}</strong> plan to the <strong>free plan</strong>.'
        free_plan_title = 'Your free plan includes:'
        features = [
            'Up to 5 subscriptions',
            'Up to 5 custom categories',
            'Up to 5 custom services',
            'Up to 10 custom service plans',
            'Basic statistics',
            'Due date notifications'
        ]
        data_kept = 'All your data has been kept. If you exceed the free plan limits, you simply won\'t be able to create new items until you delete some or upgrade to Premium.'
        can_upgrade = '<strong>You can upgrade to Premium at any time!</strong>'
        button_text = 'View Premium plans'
        hope_return = 'We hope to see you again soon among our Premium users.'
        closing = 'Best regards,<br>The Budgee Family team'
        footer_note = 'This email was sent by Budgee Family'
        contact_note = 'If you did not perform this action, please contact us immediately.'
    else:
        subject = 'Confirmation de rétrogradation - Budgee Family'
        title = 'Rétrogradation confirmée'
        greeting = f'Bonjour {user.first_name or user.email},'
        confirmation = f'Nous vous confirmons que votre compte a été rétrogradé du plan <strong>{old_plan_name}</strong> vers le <strong>plan gratuit</strong>.'
        free_plan_title = 'Votre plan gratuit comprend :'
        features = [
            'Jusqu\'à 5 abonnements',
            'Jusqu\'à 5 catégories personnalisées',
            'Jusqu\'à 5 services personnalisés',
            'Jusqu\'à 10 plans de services personnalisés',
            'Statistiques de base',
            'Notifications d\'échéance'
        ]
        data_kept = 'Toutes vos données ont été conservées. Si vous dépassez les limites du plan gratuit, vous ne pourrez simplement pas créer de nouveaux éléments jusqu\'à ce que vous en supprimiez ou que vous repassiez à Premium.'
        can_upgrade = '<strong>Vous pouvez repasser à Premium à tout moment !</strong>'
        button_text = 'Voir les plans Premium'
        hope_return = 'Nous espérons vous revoir bientôt parmi nos utilisateurs Premium.'
        closing = 'Cordialement,<br>L\'équipe Budgee Family'
        footer_note = 'Cet email a été envoyé par Budgee Family'
        contact_note = 'Si vous n\'avez pas effectué cette action, veuillez nous contacter immédiatement.'

    features_html = ''.join([f'<li>{f}</li>' for f in features])
    features_text = '\n    '.join([f'- {f}' for f in features])

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 10px 10px 0 0;
            }}
            .content {{
                background: #f9f9f9;
                padding: 30px;
                border-radius: 0 0 10px 10px;
            }}
            .info-box {{
                background: #fff3cd;
                border-left: 4px solid #f59e0b;
                padding: 15px;
                margin: 20px 0;
            }}
            .button {{
                display: inline-block;
                padding: 12px 30px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                margin-top: 20px;
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="{url_for('static', filename='uploads/logos/budgee_family_logo_trsp.png', _external=True)}" alt="Budgee Family" width="120" style="display: block; margin: 0 auto 20px auto;">
                <h1>{title}</h1>
            </div>
            <div class="content">
                <p>{greeting}</p>
                <p>{confirmation}</p>
                <div class="info-box">
                    <h3>{free_plan_title}</h3>
                    <ul>
                        {features_html}
                    </ul>
                </div>
                <p>{data_kept}</p>
                <p>{can_upgrade}</p>
                <div style="text-align: center;">
                    <a href="{url_for('main.pricing', _external=True)}" class="button">{button_text}</a>
                </div>
                <p>{hope_return}</p>
                <p>{closing}</p>
            </div>
            <div class="footer">
                <p>{footer_note}</p>
                <p>{contact_note}</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    {title}

    {greeting}

    {confirmation.replace('<strong>', '').replace('</strong>', '')}

    {free_plan_title}
    {features_text}

    {data_kept}

    {can_upgrade.replace('<strong>', '').replace('</strong>', '')}
    {url_for('main.pricing', _external=True)}

    {hope_return}

    {closing.replace('<br>', '')}
    """

    msg = Message(
        subject=subject,
        sender=os.getenv('MAIL_DEFAULT_SENDER', 'noreply@budgeefamily.com'),
        recipients=[user.email],
        body=text_body,
        html=html_body
    )

    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email : {e}")
        return False


def send_plan_upgrade_email(user, new_plan_name):
    """Envoie un email de confirmation de passage à un plan Premium avec récapitulatif détaillé"""

    # Récupérer les informations du plan
    plan = user.plan
    lang = user.language or 'fr'

    # Symbole de devise
    currency_symbols = {
        'EUR': '€', 'USD': '$', 'GBP': '£', 'CHF': 'CHF',
        'CAD': '$', 'AUD': '$', 'JPY': '¥', 'CNY': '¥',
        'INR': '₹', 'BRL': 'R$', 'MXN': '$', 'ZAR': 'R'
    }
    currency_symbol = currency_symbols.get(plan.currency, plan.currency) if plan else '€'

    # Traduction de la période de facturation
    if lang == 'en':
        billing_period_map = {
            'monthly': 'monthly',
            'yearly': 'annual',
            'lifetime': 'lifetime'
        }
    else:
        billing_period_map = {
            'monthly': 'mensuel',
            'yearly': 'annuel',
            'lifetime': 'à vie'
        }
    period_text = billing_period_map.get(plan.billing_period, plan.billing_period) if plan else ('monthly' if lang == 'en' else 'mensuel')

    # Prix formaté
    price_text = f"{plan.price:.2f} {currency_symbol}" if plan else "N/A"

    # Contenu selon la langue
    if lang == 'en':
        subject = f'✓ Welcome to {new_plan_name} - Budgee Family'
        title = '🎉 Welcome to Premium!'
        subtitle = 'Your subscription has been successfully activated'
        greeting = f'Hello {user.first_name or user.email},'
        congrats = f'Congratulations and welcome to the <strong>Budgee Family Premium</strong> family!'
        payment_success = 'We are delighted to have you among our Premium members. Your payment has been processed successfully and your subscription is now active.'
        summary_title = '📋 Your subscription summary'
        summary_plan = 'Subscribed plan'
        summary_period = 'Billing period'
        summary_amount = 'Amount'
        summary_date = 'Activation date'
        benefits_title = f'With your Premium plan, you benefit from:'
        feature_unlimited_subs = '<strong>Unlimited subscriptions</strong> - Add as many subscriptions as you want'
        feature_unlimited_cats = '<strong>Unlimited custom categories</strong> - Organize your subscriptions your way'
        feature_unlimited_svcs = '<strong>Unlimited custom services</strong> - Create your own services'
        feature_unlimited_plans = '<strong>Unlimited service plans</strong> - Manage all your pricing plans'
        feature_advanced_stats = '<strong>Advanced statistics</strong> - Analyze your expenses in detail'
        feature_export = '<strong>Data export</strong> - Download your data whenever you want'
        feature_support = '<strong>Priority support</strong> - Fast and personalized assistance'
        button_dashboard = '🚀 Access my dashboard'
        invoice_note = 'You will also receive your invoice in a separate email. You can find it anytime in your customer area.'
        thanks_note = 'Thank you for your trust! We are here to support you in managing your subscriptions.'
        footer_title = 'Budgee Family - Smart subscription manager'
        footer_website = 'Website'
        footer_contact = 'Contact'
        footer_legal = 'Legal notice'
    else:
        subject = f'✓ Bienvenue sur {new_plan_name} - Budgee Family'
        title = '🎉 Bienvenue chez Premium !'
        subtitle = 'Votre abonnement a été activé avec succès'
        greeting = f'Bonjour {user.first_name or user.email},'
        congrats = f'Félicitations et bienvenue dans la famille <strong>Budgee Family Premium</strong> !'
        payment_success = 'Nous sommes ravis de vous compter parmi nos membres Premium. Votre paiement a été traité avec succès et votre abonnement est désormais actif.'
        summary_title = '📋 Récapitulatif de votre abonnement'
        summary_plan = 'Plan souscrit'
        summary_period = 'Période de facturation'
        summary_amount = 'Montant'
        summary_date = 'Date d\'activation'
        benefits_title = f'Avec votre plan Premium, vous bénéficiez de :'
        feature_unlimited_subs = '<strong>Abonnements illimités</strong> - Ajoutez autant d\'abonnements que vous le souhaitez'
        feature_unlimited_cats = '<strong>Catégories personnalisées illimitées</strong> - Organisez vos abonnements à votre façon'
        feature_unlimited_svcs = '<strong>Services personnalisés illimités</strong> - Créez vos propres services'
        feature_unlimited_plans = '<strong>Plans de services illimités</strong> - Gérez tous vos plans tarifaires'
        feature_advanced_stats = '<strong>Statistiques avancées</strong> - Analysez vos dépenses en détail'
        feature_export = '<strong>Export de données</strong> - Téléchargez vos données quand vous voulez'
        feature_support = '<strong>Support prioritaire</strong> - Une assistance rapide et personnalisée'
        button_dashboard = '🚀 Accéder à mon tableau de bord'
        invoice_note = 'Vous recevrez également votre facture dans un email séparé. Vous pourrez la retrouver à tout moment dans votre espace client.'
        thanks_note = 'Merci de votre confiance ! Nous sommes là pour vous accompagner dans la gestion de vos abonnements.'
        footer_title = 'Budgee Family - Gestionnaire d\'abonnements intelligent'
        footer_website = 'Site web'
        footer_contact = 'Contact'
        footer_legal = 'Mentions légales'

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f8f9fa;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                background-color: #ffffff;
                border-radius: 15px;
                overflow: hidden;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                color: white;
                padding: 40px 30px;
                text-align: center;
            }}
            .logo-container {{
                margin-bottom: 20px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: bold;
            }}
            .header p {{
                margin: 10px 0 0 0;
                opacity: 0.95;
                font-size: 16px;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .content h2 {{
                color: #6366f1;
                font-size: 22px;
                margin-top: 0;
                margin-bottom: 20px;
            }}
            .subscription-summary {{
                background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
                border-left: 4px solid #6366f1;
                padding: 25px;
                margin: 25px 0;
                border-radius: 8px;
            }}
            .subscription-summary h3 {{
                color: #6366f1;
                margin-top: 0;
                margin-bottom: 15px;
                font-size: 18px;
            }}
            .summary-item {{
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid rgba(99, 102, 241, 0.2);
            }}
            .summary-item:last-child {{
                border-bottom: none;
                font-weight: bold;
                font-size: 1.1em;
                color: #6366f1;
                margin-top: 10px;
            }}
            .summary-label {{
                color: #1e40af;
                font-weight: 500;
            }}
            .summary-value {{
                color: #6366f1;
                font-weight: 600;
            }}
            .feature-list {{
                margin: 25px 0;
                background: #ffffff;
                border-radius: 8px;
                padding: 20px;
            }}
            .feature-item {{
                padding: 10px 0;
                border-bottom: 1px solid #e5e7eb;
                display: flex;
                align-items: center;
            }}
            .feature-item:last-child {{
                border-bottom: none;
            }}
            .feature-icon {{
                color: #10b981;
                margin-right: 10px;
                font-size: 18px;
            }}
            .button {{
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                margin: 20px 0;
                font-weight: 600;
                text-align: center;
            }}
            .footer {{
                background-color: #f8f9fa;
                padding: 25px;
                text-align: center;
                color: #6b7280;
                font-size: 13px;
                border-top: 1px solid #e5e7eb;
            }}
            .footer a {{
                color: #6366f1;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo-container">
                    <img src="{url_for('static', filename='uploads/logos/budgee_family_logo_trsp.png', _external=True)}" alt="Budgee Family" width="120" style="display: block; margin: 0 auto;">
                </div>
                <h1>{title}</h1>
                <p>{subtitle}</p>
            </div>

            <div class="content">
                <h2>{greeting}</h2>

                <p>{congrats}</p>

                <p>{payment_success}</p>

                <div class="subscription-summary">
                    <h3>{summary_title}</h3>
                    <div class="summary-item">
                        <span class="summary-label">{summary_plan}</span>
                        <span class="summary-value">{new_plan_name}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">{summary_period}</span>
                        <span class="summary-value">{period_text.capitalize()}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">{summary_amount}</span>
                        <span class="summary-value">{price_text}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">{summary_date}</span>
                        <span class="summary-value">{datetime.now().strftime('%d/%m/%Y')}</span>
                    </div>
                </div>

                <p><strong>{benefits_title}</strong></p>

                <div class="feature-list">
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        {feature_unlimited_subs}
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        {feature_unlimited_cats}
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        {feature_unlimited_svcs}
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        {feature_unlimited_plans}
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        {feature_advanced_stats}
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        {feature_export}
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        {feature_support}
                    </div>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{url_for('main.dashboard', _external=True)}" class="button" style="color: white;">
                        {button_dashboard}
                    </a>
                </div>

                <p>{invoice_note}</p>

                <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
                    <em>{thanks_note}</em>
                </p>
            </div>

            <div class="footer">
                <p><strong>Budgee Family</strong> - {footer_title.split(' - ')[1]}</p>
                <p style="margin-top: 8px;">
                    <a href="https://budgeefamily.com">{footer_website}</a> •
                    <a href="https://budgeefamily.com/contact">{footer_contact}</a> •
                    <a href="https://budgeefamily.com/mentions-legales">{footer_legal}</a>
                </p>
                <p style="margin-top: 15px; font-size: 12px; color: #9ca3af;">
                    © {datetime.now().year} Budgee Family. {'All rights reserved.' if lang == 'en' else 'Tous droits réservés.'}
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    # Formater les features pour le texte
    feature_texts = [
        feature_unlimited_subs.replace('<strong>', '').replace('</strong>', ''),
        feature_unlimited_cats.replace('<strong>', '').replace('</strong>', ''),
        feature_unlimited_svcs.replace('<strong>', '').replace('</strong>', ''),
        feature_unlimited_plans.replace('<strong>', '').replace('</strong>', ''),
        feature_advanced_stats.replace('<strong>', '').replace('</strong>', ''),
        feature_export.replace('<strong>', '').replace('</strong>', ''),
        feature_support.replace('<strong>', '').replace('</strong>', '')
    ]
    features_text = '\n    ✓ '.join(feature_texts)

    text_body = f"""
    {title}

    {greeting}

    {congrats.replace('<strong>', '').replace('</strong>', '')}

    {payment_success}

    {summary_title.upper()}

    {summary_plan} : {new_plan_name}
    {summary_period} : {period_text.capitalize()}
    {summary_amount} : {price_text}
    {summary_date} : {datetime.now().strftime('%d/%m/%Y')}

    {benefits_title.upper().replace('<STRONG>', '').replace('</STRONG>', '')}

    ✓ {features_text}

    {button_dashboard} : {url_for('main.dashboard', _external=True)}

    {invoice_note}

    {thanks_note}

    ---
    Budgee Family - {footer_title.split(' - ')[1]}
    {footer_website} : https://budgeefamily.com
    {footer_contact} : https://budgeefamily.com/contact

    © {datetime.now().year} Budgee Family. {'All rights reserved.' if lang == 'en' else 'Tous droits réservés.'}
    """

    msg = Message(
        subject=subject,
        sender=os.getenv('MAIL_DEFAULT_SENDER', 'noreply@budgeefamily.com'),
        recipients=[user.email],
        body=text_body,
        html=html_body
    )

    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email : {e}")
        return False


def send_contact_confirmation_email(name, email, language='fr'):
    """Envoie un email de confirmation après l'envoi d'un message via le formulaire de contact"""

    lang = language or 'fr'

    # Contenu selon la langue
    if lang == 'en':
        subject = '✓ Message received - Budgee Family'
        title = 'Message received!'
        subtitle = 'Thank you for contacting us'
        greeting = f'Hello {name},'
        received_msg = 'We have received your message and thank you for your interest in <strong>Budgee Family</strong>.'
        request_registered = '✓ Your request has been registered'
        response_time = 'Our team will get back to you within <strong>24 to 48 hours</strong>.'
        meanwhile = 'In the meantime, did you know that Budgee Family allows you to:'
        feature_manage = '<strong>Manage all your subscriptions</strong> in one place'
        feature_notifications = '<strong>Receive notifications</strong> before each renewal'
        feature_visualize = '<strong>Visualize your monthly expenses</strong> in real time'
        feature_organize = '<strong>Organize by categories</strong> with custom logos'
        button_discover = '🚀 Discover Budgee Family'
        no_action = 'This email confirms the receipt of your message. You have no action to take.'
        footer_title = 'Smart subscription manager'
        footer_website = 'Website'
        footer_contact = 'Contact'
        footer_legal = 'Legal notice'
    else:
        subject = '✓ Message reçu - Budgee Family'
        title = 'Message bien reçu !'
        subtitle = 'Merci de nous avoir contactés'
        greeting = f'Bonjour {name},'
        received_msg = 'Nous avons bien reçu votre message et nous vous remercions de l\'intérêt que vous portez à <strong>Budgee Family</strong>.'
        request_registered = '✓ Votre demande a été enregistrée'
        response_time = 'Notre équipe reviendra vers vous dans les <strong>24 à 48 heures</strong>.'
        meanwhile = 'En attendant notre réponse, saviez-vous que Budgee Family vous permet de :'
        feature_manage = '<strong>Gérer tous vos abonnements</strong> en un seul endroit'
        feature_notifications = '<strong>Recevoir des notifications</strong> avant chaque renouvellement'
        feature_visualize = '<strong>Visualiser vos dépenses</strong> mensuelles en temps réel'
        feature_organize = '<strong>Organiser par catégories</strong> avec logos personnalisés'
        button_discover = '🚀 Découvrir Budgee Family'
        no_action = 'Cet email confirme la réception de votre message. Vous n\'avez aucune action à effectuer.'
        footer_title = 'Gestionnaire d\'abonnements intelligent'
        footer_website = 'Site web'
        footer_contact = 'Contact'
        footer_legal = 'Mentions légales'

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f8f9fa;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                background-color: #ffffff;
                border-radius: 15px;
                overflow: hidden;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                color: white;
                padding: 40px 30px;
                text-align: center;
            }}
            .logo-container {{
                margin-bottom: 20px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: bold;
            }}
            .header p {{
                margin: 10px 0 0 0;
                opacity: 0.95;
                font-size: 16px;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .content h2 {{
                color: #6366f1;
                font-size: 22px;
                margin-top: 0;
                margin-bottom: 20px;
            }}
            .info-box {{
                background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
                border-left: 4px solid #6366f1;
                padding: 20px;
                margin: 25px 0;
                border-radius: 8px;
            }}
            .info-box p {{
                margin: 0;
                color: #1e40af;
            }}
            .info-box strong {{
                color: #6366f1;
            }}
            .feature-list {{
                margin: 25px 0;
            }}
            .feature-item {{
                padding: 10px 0;
                border-bottom: 1px solid #e5e7eb;
            }}
            .feature-item:last-child {{
                border-bottom: none;
            }}
            .feature-item i {{
                color: #10b981;
                margin-right: 10px;
            }}
            .button {{
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                margin: 20px 0;
                font-weight: 600;
                text-align: center;
            }}
            .footer {{
                background-color: #f8f9fa;
                padding: 25px;
                text-align: center;
                color: #6b7280;
                font-size: 13px;
                border-top: 1px solid #e5e7eb;
            }}
            .footer a {{
                color: #6366f1;
                text-decoration: none;
            }}
            .social-links {{
                margin-top: 15px;
            }}
            .social-links a {{
                display: inline-block;
                margin: 0 8px;
                color: #6366f1;
                font-size: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo-container">
                    <img src="{url_for('static', filename='uploads/logos/budgee_family_logo_trsp.png', _external=True)}" alt="Budgee Family" width="120" style="display: block; margin: 0 auto;">
                </div>
                <h1>{title}</h1>
                <p>{subtitle}</p>
            </div>

            <div class="content">
                <h2>{greeting}</h2>

                <p>{received_msg}</p>

                <div class="info-box">
                    <p><strong>{request_registered}</strong></p>
                    <p style="margin-top: 10px;">{response_time}</p>
                </div>

                <p>{meanwhile}</p>

                <div class="feature-list">
                    <div class="feature-item">
                        ✓ {feature_manage}
                    </div>
                    <div class="feature-item">
                        ✓ {feature_notifications}
                    </div>
                    <div class="feature-item">
                        ✓ {feature_visualize}
                    </div>
                    <div class="feature-item">
                        ✓ {feature_organize}
                    </div>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://budgeefamily.com" class="button" style="color: white;">
                        {button_discover}
                    </a>
                </div>

                <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
                    <em>{no_action}</em>
                </p>
            </div>

            <div class="footer">
                <p><strong>Budgee Family</strong> - {footer_title}</p>
                <p style="margin-top: 8px;">
                    <a href="https://budgeefamily.com">{footer_website}</a> •
                    <a href="https://budgeefamily.com/contact">{footer_contact}</a> •
                    <a href="https://budgeefamily.com/mentions-legales">{footer_legal}</a>
                </p>
                <p style="margin-top: 15px; font-size: 12px; color: #9ca3af;">
                    © {datetime.now().year} Budgee Family. {'All rights reserved.' if lang == 'en' else 'Tous droits réservés.'}
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    {title}

    {greeting}

    {received_msg.replace('<strong>', '').replace('</strong>', '')}

    {request_registered}
    {response_time.replace('<strong>', '').replace('</strong>', '')}

    {meanwhile}
    ✓ {feature_manage.replace('<strong>', '').replace('</strong>', '')}
    ✓ {feature_notifications.replace('<strong>', '').replace('</strong>', '')}
    ✓ {feature_visualize.replace('<strong>', '').replace('</strong>', '')}
    ✓ {feature_organize.replace('<strong>', '').replace('</strong>', '')}

    {button_discover} : https://budgeefamily.com

    {no_action}

    ---
    Budgee Family - {footer_title}
    {footer_website} : https://budgeefamily.com
    {footer_contact} : https://budgeefamily.com/contact

    © {datetime.now().year} Budgee Family. {'All rights reserved.' if lang == 'en' else 'Tous droits réservés.'}
    """

    msg = Message(
        subject=subject,
        sender=os.getenv('MAIL_DEFAULT_SENDER', 'noreply@budgeefamily.com'),
        recipients=[email],
        body=text_body,
        html=html_body
    )

    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email de confirmation : {e}")
        return False


def send_welcome_email(user):
    """Envoie un email de bienvenue avec récapitulatif du plan souscrit lors de l'inscription"""

    # Récupérer les informations du plan
    plan = user.plan
    lang = user.language or 'fr'

    # Déterminer si c'est un plan gratuit ou premium
    is_free_plan = not (plan and plan.is_premium())

    # Symbole de devise
    currency_symbols = {
        'EUR': '€', 'USD': '$', 'GBP': '£', 'CHF': 'CHF',
        'CAD': '$', 'AUD': '$', 'JPY': '¥', 'CNY': '¥',
        'INR': '₹', 'BRL': 'R$', 'MXN': '$', 'ZAR': 'R'
    }
    currency_symbol = currency_symbols.get(plan.currency, plan.currency) if plan else '€'

    # Traduction de la période de facturation
    if lang == 'en':
        billing_period_map = {
            'monthly': 'monthly',
            'yearly': 'annual',
            'lifetime': 'lifetime'
        }
        period_text = billing_period_map.get(plan.billing_period, plan.billing_period) if plan else 'free'
        price_text = f"{plan.price:.2f} {currency_symbol}" if plan and plan.price > 0 else "Free"
    else:
        billing_period_map = {
            'monthly': 'mensuel',
            'yearly': 'annuel',
            'lifetime': 'à vie'
        }
        period_text = billing_period_map.get(plan.billing_period, plan.billing_period) if plan else 'gratuit'
        price_text = f"{plan.price:.2f} {currency_symbol}" if plan and plan.price > 0 else "Gratuit"

    # Nom du plan
    plan_name = plan.name if plan else "Free"

    # Contenu selon la langue
    if lang == 'en':
        subject = f'✓ Welcome to Budgee Family - {plan_name} Plan'
        title = '🎉 Welcome to Budgee Family!'
        subtitle = 'Your account has been successfully created'
        greeting = f'Hello {user.first_name or user.email},'
        thanks_signup = 'Thank you for signing up to <strong>Budgee Family</strong>, your smart subscription manager!'
        welcome_msg = 'We are delighted to welcome you and wish you a warm welcome to our community.'
        summary_title = '📋 Your subscription summary'
        summary_plan = 'Subscribed plan'
        summary_type = 'Subscription type'
        summary_price = 'Price'
        summary_date = 'Registration date'
        benefits_title = f'With your {plan_name} plan, you benefit from:'
        button_dashboard = '🚀 Access my dashboard'
        thanks_note = 'Thank you for your trust! We are here to support you in managing your subscriptions.'
        footer_title = 'Smart subscription manager'
        footer_website = 'Website'
        footer_contact = 'Contact'
        footer_legal = 'Legal notice'
    else:
        subject = f'✓ Bienvenue sur Budgee Family - Plan {plan_name}'
        title = '🎉 Bienvenue sur Budgee Family !'
        subtitle = 'Votre compte a été créé avec succès'
        greeting = f'Bonjour {user.first_name or user.email},'
        thanks_signup = 'Merci de vous être inscrit sur <strong>Budgee Family</strong>, votre gestionnaire d\'abonnements intelligent !'
        welcome_msg = 'Nous sommes ravis de vous accueillir et vous souhaitons la bienvenue dans notre communauté.'
        summary_title = '📋 Récapitulatif de votre abonnement'
        summary_plan = 'Plan souscrit'
        summary_type = 'Type d\'abonnement'
        summary_price = 'Tarif'
        summary_date = 'Date d\'inscription'
        benefits_title = f'Avec votre plan {plan_name}, vous bénéficiez de :'
        button_dashboard = '🚀 Accéder à mon tableau de bord'
        thanks_note = 'Merci de votre confiance ! Nous sommes là pour vous accompagner dans la gestion de vos abonnements.'
        footer_title = 'Gestionnaire d\'abonnements intelligent'
        footer_website = 'Site web'
        footer_contact = 'Contact'
        footer_legal = 'Mentions légales'

    # Contenu spécifique selon le type de plan
    if is_free_plan:
        if lang == 'en':
            features_html = """
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Up to 5 subscriptions</strong> - Manage your main subscriptions
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Up to 5 custom categories</strong> - Organize as you wish
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Up to 5 custom services</strong> - Create your own services
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Up to 10 service plans</strong> - Manage your pricing plans
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Basic statistics</strong> - Track your expenses
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Due date notifications</strong> - Don't miss any renewal
                    </div>"""

            features_text = """✓ Up to 5 subscriptions - Manage your main subscriptions
    ✓ Up to 5 custom categories - Organize as you wish
    ✓ Up to 5 custom services - Create your own services
    ✓ Up to 10 service plans - Manage your pricing plans
    ✓ Basic statistics - Track your expenses
    ✓ Due date notifications - Don't miss any renewal"""

            upgrade_section_html = """
                <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-left: 4px solid #f59e0b; padding: 20px; margin: 25px 0; border-radius: 8px;">
                    <p style="margin: 0; color: #92400e; font-weight: 600;">💡 Want more?</p>
                    <p style="margin: 10px 0 0 0; color: #92400e;">Upgrade to Premium to unlock unlimited subscriptions, advanced statistics and much more!</p>
                    <div style="text-align: center; margin-top: 15px;">
                        <a href="{url_for('main.pricing', _external=True)}" style="display: inline-block; padding: 10px 24px; background: #f59e0b; color: white; text-decoration: none; border-radius: 6px; font-weight: 600;">Discover Premium</a>
                    </div>
                </div>"""

            upgrade_section_text = """
    💡 WANT MORE?

    Upgrade to Premium to unlock unlimited subscriptions, advanced statistics and much more!
    Discover Premium : {url_for('main.pricing', _external=True)}"""
        else:
            features_html = """
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Jusqu'à 5 abonnements</strong> - Gérez vos principaux abonnements
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Jusqu'à 5 catégories personnalisées</strong> - Organisez comme vous voulez
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Jusqu'à 5 services personnalisés</strong> - Créez vos propres services
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Jusqu'à 10 plans de services</strong> - Gérez vos plans tarifaires
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Statistiques de base</strong> - Suivez vos dépenses
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Notifications d'échéance</strong> - Ne ratez aucun renouvellement
                    </div>"""

            features_text = """✓ Jusqu'à 5 abonnements - Gérez vos principaux abonnements
    ✓ Jusqu'à 5 catégories personnalisées - Organisez comme vous voulez
    ✓ Jusqu'à 5 services personnalisés - Créez vos propres services
    ✓ Jusqu'à 10 plans de services - Gérez vos plans tarifaires
    ✓ Statistiques de base - Suivez vos dépenses
    ✓ Notifications d'échéance - Ne ratez aucun renouvellement"""

            upgrade_section_html = """
                <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-left: 4px solid #f59e0b; padding: 20px; margin: 25px 0; border-radius: 8px;">
                    <p style="margin: 0; color: #92400e; font-weight: 600;">💡 Envie de plus ?</p>
                    <p style="margin: 10px 0 0 0; color: #92400e;">Passez à Premium pour débloquer des abonnements illimités, des statistiques avancées et bien plus encore !</p>
                    <div style="text-align: center; margin-top: 15px;">
                        <a href="{url_for('main.pricing', _external=True)}" style="display: inline-block; padding: 10px 24px; background: #f59e0b; color: white; text-decoration: none; border-radius: 6px; font-weight: 600;">Découvrir Premium</a>
                    </div>
                </div>"""

            upgrade_section_text = """
    💡 ENVIE DE PLUS ?

    Passez à Premium pour débloquer des abonnements illimités, des statistiques avancées et bien plus encore !
    Découvrir Premium : {url_for('main.pricing', _external=True)}"""

    else:
        if lang == 'en':
            features_html = """
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Unlimited subscriptions</strong> - Add as many subscriptions as you want
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Unlimited custom categories</strong> - Organize your subscriptions your way
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Unlimited custom services</strong> - Create your own services
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Unlimited service plans</strong> - Manage all your pricing plans
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Advanced statistics</strong> - Analyze your expenses in detail
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Data export</strong> - Download your data whenever you want
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Priority support</strong> - Fast and personalized assistance
                    </div>"""

            features_text = """✓ Unlimited subscriptions - Add as many subscriptions as you want
    ✓ Unlimited custom categories - Organize your subscriptions your way
    ✓ Unlimited custom services - Create your own services
    ✓ Unlimited service plans - Manage all your pricing plans
    ✓ Advanced statistics - Analyze your expenses in detail
    ✓ Data export - Download your data whenever you want
    ✓ Priority support - Fast and personalized assistance"""
        else:
            features_html = """
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Abonnements illimités</strong> - Ajoutez autant d'abonnements que vous le souhaitez
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Catégories personnalisées illimitées</strong> - Organisez vos abonnements à votre façon
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Services personnalisés illimités</strong> - Créez vos propres services
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Plans de services illimités</strong> - Gérez tous vos plans tarifaires
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Statistiques avancées</strong> - Analysez vos dépenses en détail
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Export de données</strong> - Téléchargez vos données quand vous voulez
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">✓</span>
                        <strong>Support prioritaire</strong> - Une assistance rapide et personnalisée
                    </div>"""

            features_text = """✓ Abonnements illimités - Ajoutez autant d'abonnements que vous le souhaitez
    ✓ Catégories personnalisées illimitées - Organisez vos abonnements à votre façon
    ✓ Services personnalisés illimités - Créez vos propres services
    ✓ Plans de services illimités - Gérez tous vos plans tarifaires
    ✓ Statistiques avancées - Analysez vos dépenses en détail
    ✓ Export de données - Téléchargez vos données quand vous voulez
    ✓ Support prioritaire - Une assistance rapide et personnalisée"""

        upgrade_section_html = ""
        upgrade_section_text = ""

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f8f9fa;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                background-color: #ffffff;
                border-radius: 15px;
                overflow: hidden;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                color: white;
                padding: 40px 30px;
                text-align: center;
            }}
            .logo-container {{
                margin-bottom: 20px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: bold;
            }}
            .header p {{
                margin: 10px 0 0 0;
                opacity: 0.95;
                font-size: 16px;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .content h2 {{
                color: #6366f1;
                font-size: 22px;
                margin-top: 0;
                margin-bottom: 20px;
            }}
            .subscription-summary {{
                background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
                border-left: 4px solid #6366f1;
                padding: 25px;
                margin: 25px 0;
                border-radius: 8px;
            }}
            .subscription-summary h3 {{
                color: #6366f1;
                margin-top: 0;
                margin-bottom: 15px;
                font-size: 18px;
            }}
            .summary-item {{
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid rgba(99, 102, 241, 0.2);
            }}
            .summary-item:last-child {{
                border-bottom: none;
            }}
            .summary-label {{
                color: #1e40af;
                font-weight: 500;
            }}
            .summary-value {{
                color: #6366f1;
                font-weight: 600;
            }}
            .feature-list {{
                margin: 25px 0;
                background: #ffffff;
                border-radius: 8px;
                padding: 20px;
            }}
            .feature-item {{
                padding: 10px 0;
                border-bottom: 1px solid #e5e7eb;
                display: flex;
                align-items: center;
            }}
            .feature-item:last-child {{
                border-bottom: none;
            }}
            .feature-icon {{
                color: #10b981;
                margin-right: 10px;
                font-size: 18px;
            }}
            .button {{
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                margin: 20px 0;
                font-weight: 600;
                text-align: center;
            }}
            .footer {{
                background-color: #f8f9fa;
                padding: 25px;
                text-align: center;
                color: #6b7280;
                font-size: 13px;
                border-top: 1px solid #e5e7eb;
            }}
            .footer a {{
                color: #6366f1;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo-container">
                    <img src="{url_for('static', filename='uploads/logos/budgee_family_logo_trsp.png', _external=True)}" alt="Budgee Family" width="120" style="display: block; margin: 0 auto;">
                </div>
                <h1>{title}</h1>
                <p>{subtitle}</p>
            </div>

            <div class="content">
                <h2>{greeting}</h2>

                <p>{thanks_signup}</p>

                <p>{welcome_msg}</p>

                <div class="subscription-summary">
                    <h3>{summary_title}</h3>
                    <div class="summary-item">
                        <span class="summary-label">{summary_plan}</span>
                        <span class="summary-value">{plan_name}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">{summary_type}</span>
                        <span class="summary-value">{period_text.capitalize()}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">{summary_price}</span>
                        <span class="summary-value">{price_text}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">{summary_date}</span>
                        <span class="summary-value">{datetime.now().strftime('%d/%m/%Y')}</span>
                    </div>
                </div>

                <p><strong>{benefits_title}</strong></p>

                <div class="feature-list">
{features_html}
                </div>

{upgrade_section_html}

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{url_for('main.dashboard', _external=True)}" class="button" style="color: white;">
                        {button_dashboard}
                    </a>
                </div>

                <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
                    <em>{thanks_note}</em>
                </p>
            </div>

            <div class="footer">
                <p><strong>Budgee Family</strong> - {footer_title}</p>
                <p style="margin-top: 8px;">
                    <a href="https://budgeefamily.com">{footer_website}</a> •
                    <a href="https://budgeefamily.com/contact">{footer_contact}</a> •
                    <a href="https://budgeefamily.com/mentions-legales">{footer_legal}</a>
                </p>
                <p style="margin-top: 15px; font-size: 12px; color: #9ca3af;">
                    © {datetime.now().year} Budgee Family. {'All rights reserved.' if lang == 'en' else 'Tous droits réservés.'}
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    {title}

    {greeting}

    {thanks_signup.replace('<strong>', '').replace('</strong>', '')}

    {welcome_msg}

    {summary_title.upper()}

    {summary_plan} : {plan_name}
    {summary_type} : {period_text.capitalize()}
    {summary_price} : {price_text}
    {summary_date} : {datetime.now().strftime('%d/%m/%Y')}

    {benefits_title.upper().replace('<STRONG>', '').replace('</STRONG>', '')}

    {features_text}
{upgrade_section_text}

    {button_dashboard} : {url_for('main.dashboard', _external=True)}

    {thanks_note}

    ---
    Budgee Family - {footer_title}
    {footer_website} : https://budgeefamily.com
    {footer_contact} : https://budgeefamily.com/contact

    © {datetime.now().year} Budgee Family. {'All rights reserved.' if lang == 'en' else 'Tous droits réservés.'}
    """

    msg = Message(
        subject=subject,
        sender=os.getenv('MAIL_DEFAULT_SENDER', 'noreply@budgeefamily.com'),
        recipients=[user.email],
        body=text_body,
        html=html_body
    )

    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email de bienvenue : {e}")
        return False


def send_new_subscription_notification(user):
    """Envoie un email de notification à l'équipe lors d'une nouvelle inscription"""

    # Récupérer les informations du plan
    plan = user.plan
    plan_name = plan.name if plan else "Free"
    is_premium = plan and plan.is_premium()

    # Symbole de devise
    currency_symbols = {
        'EUR': '€', 'USD': '$', 'GBP': '£', 'CHF': 'CHF',
        'CAD': '$', 'AUD': '$', 'JPY': '¥', 'CNY': '¥',
        'INR': '₹', 'BRL': 'R$', 'MXN': '$', 'ZAR': 'R'
    }
    currency_symbol = currency_symbols.get(plan.currency, plan.currency) if plan else '€'

    # Prix formaté
    price_text = f"{plan.price:.2f} {currency_symbol}" if plan and plan.price > 0 else "Gratuit"

    # Badge du plan
    plan_badge_color = "#10b981" if is_premium else "#6b7280"
    plan_badge_bg = "#d1fae5" if is_premium else "#f3f4f6"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f8f9fa;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                background-color: #ffffff;
                border-radius: 15px;
                overflow: hidden;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: bold;
            }}
            .header p {{
                margin: 10px 0 0 0;
                opacity: 0.95;
                font-size: 14px;
            }}
            .content {{
                padding: 30px;
            }}
            .plan-badge {{
                display: inline-block;
                padding: 6px 16px;
                background: {plan_badge_bg};
                color: {plan_badge_color};
                border-radius: 20px;
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 20px;
            }}
            .info-grid {{
                background: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
            }}
            .info-item {{
                display: flex;
                padding: 12px 0;
                border-bottom: 1px solid #e5e7eb;
            }}
            .info-item:last-child {{
                border-bottom: none;
            }}
            .info-label {{
                font-weight: 600;
                color: #6b7280;
                width: 140px;
                flex-shrink: 0;
            }}
            .info-value {{
                color: #1f2937;
                flex-grow: 1;
            }}
            .footer {{
                background-color: #f8f9fa;
                padding: 20px;
                text-align: center;
                color: #6b7280;
                font-size: 12px;
                border-top: 1px solid #e5e7eb;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="{url_for('static', filename='uploads/logos/budgee_family_logo_trsp.png', _external=True)}" alt="Budgee Family" width="120" style="display: block; margin: 0 auto 20px auto;">
                <h1>🎉 Nouvelle inscription !</h1>
                <p>Un nouveau client vient de s'inscrire sur Budgee Family</p>
            </div>

            <div class="content">
                <div style="text-align: center;">
                    <span class="plan-badge">{'⭐ ' if is_premium else ''}Plan {plan_name}</span>
                </div>

                <div class="info-grid">
                    <div class="info-item">
                        <span class="info-label">Nom complet</span>
                        <span class="info-value"><strong>{user.first_name or ''} {user.last_name or ''}</strong></span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Email</span>
                        <span class="info-value"><a href="mailto:{user.email}">{user.email}</a></span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Plan souscrit</span>
                        <span class="info-value">{plan_name}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Tarif</span>
                        <span class="info-value">{price_text}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Pays</span>
                        <span class="info-value">{user.country or 'Non renseigné'}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Devise par défaut</span>
                        <span class="info-value">{user.default_currency}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Fuseau horaire</span>
                        <span class="info-value">{user.timezone or 'Non renseigné'}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Date d'inscription</span>
                        <span class="info-value">{datetime.now().strftime('%d/%m/%Y à %H:%M')}</span>
                    </div>
                </div>

                {'<p style="background: #d1fae5; border-left: 4px solid #10b981; padding: 15px; border-radius: 6px; margin: 20px 0;"><strong>💰 Inscription Premium !</strong><br>Ce client a souscrit à un plan payant.</p>' if is_premium else ''}
            </div>

            <div class="footer">
                <p><strong>Budgee Family</strong> - Notification automatique d'inscription</p>
                <p style="margin-top: 8px; color: #9ca3af;">© {datetime.now().year} Budgee Family. Tous droits réservés.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    🎉 NOUVELLE INSCRIPTION SUR BUDGEE FAMILY

    Un nouveau client vient de s'inscrire !

    {'⭐ INSCRIPTION PREMIUM !' if is_premium else ''}

    INFORMATIONS DU CLIENT
    ----------------------
    Nom complet : {user.first_name or ''} {user.last_name or ''}
    Email : {user.email}
    Plan souscrit : {plan_name}
    Tarif : {price_text}
    Pays : {user.country or 'Non renseigné'}
    Devise par défaut : {user.default_currency}
    Fuseau horaire : {user.timezone or 'Non renseigné'}
    Date d'inscription : {datetime.now().strftime('%d/%m/%Y à %H:%M')}

    {'💰 Ce client a souscrit à un plan payant !' if is_premium else ''}

    ---
    Budgee Family - Notification automatique d'inscription
    © {datetime.now().year} Budgee Family. Tous droits réservés.
    """

    msg = Message(
        subject=f"{'⭐ ' if is_premium else ''}Nouvelle inscription Budgee Family - {plan_name}",
        sender=os.getenv('MAIL_DEFAULT_SENDER', 'noreply@budgeefamily.com'),
        recipients=['contact@budgeefamily.com'],
        reply_to=user.email,
        body=text_body,
        html=html_body
    )

    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erreur lors de l'envoi de la notification d'inscription : {e}")
        return False


def send_invoice_email(user, invoice_id):
    """Envoie un email avec la facture Stripe à l'utilisateur"""
    try:
        lang = user.language or 'fr'

        # Initialiser Stripe
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

        # Récupérer la facture depuis Stripe
        invoice = stripe.Invoice.retrieve(invoice_id)

        # Extraire les informations de la facture
        invoice_number = invoice.get('number', 'N/A')
        invoice_pdf_url = invoice.get('invoice_pdf')
        hosted_invoice_url = invoice.get('hosted_invoice_url')
        amount_paid = invoice.get('amount_paid', 0) / 100  # Convertir de centimes en unités
        currency = invoice.get('currency', 'eur').upper()
        invoice_date = invoice.get('created')

        # Convertir le timestamp en date lisible
        from datetime import datetime
        invoice_date_str = datetime.fromtimestamp(invoice_date).strftime('%d/%m/%Y')

        # Symbole de devise
        currency_symbols = {
            'EUR': '€', 'USD': '$', 'GBP': '£', 'CHF': 'CHF',
            'CAD': '$', 'AUD': '$', 'JPY': '¥', 'CNY': '¥',
            'INR': '₹', 'BRL': 'R$', 'MXN': '$', 'ZAR': 'R'
        }
        currency_symbol = currency_symbols.get(currency, currency)

        # Contenu selon la langue
        if lang == 'en':
            subject = f'Your Budgee Family invoice #{invoice_number}'
            title = '📄 Your Budgee Family invoice'
            greeting = f'Hello {user.first_name or user.email},'
            thanks_payment = 'Thank you for your payment! Here is your invoice for your <strong>Budgee Family Premium</strong> subscription.'
            invoice_num_label = 'Invoice number:'
            date_label = 'Date:'
            amount_label = 'Amount paid:'
            download_title = '<strong>Download your invoice:</strong>'
            button_download = '📥 Download PDF invoice'
            button_view = '👁️ View invoice online'
            auto_generated = 'This invoice is automatically generated for your Premium subscription. You can download and keep it for your records.'
            thanks_closing = 'Thank you for your trust!'
            closing = 'Best regards,<br>The Budgee Family team'
            footer_note = 'This email was sent by Budgee Family'
            footer_question = 'If you have any questions about your invoice, please don\'t hesitate to contact us.'
        else:
            subject = f'Votre facture Budgee Family #{invoice_number}'
            title = '📄 Votre facture Budgee Family'
            greeting = f'Bonjour {user.first_name or user.email},'
            thanks_payment = 'Merci pour votre paiement ! Voici votre facture pour votre abonnement <strong>Budgee Family Premium</strong>.'
            invoice_num_label = 'Numéro de facture :'
            date_label = 'Date :'
            amount_label = 'Montant payé :'
            download_title = '<strong>Télécharger votre facture :</strong>'
            button_download = '📥 Télécharger la facture PDF'
            button_view = '👁️ Voir la facture en ligne'
            auto_generated = 'Cette facture est générée automatiquement pour votre abonnement Premium. Vous pouvez la télécharger et la conserver pour vos dossiers.'
            thanks_closing = 'Merci de votre confiance !'
            closing = 'Cordialement,<br>L\'équipe Budgee Family'
            footer_note = 'Cet email a été envoyé par Budgee Family'
            footer_question = 'Si vous avez des questions concernant votre facture, n\'hésitez pas à nous contacter.'

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .invoice-box {{
                    background: white;
                    border: 2px solid #667eea;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                }}
                .invoice-detail {{
                    display: flex;
                    justify-content: space-between;
                    padding: 10px 0;
                    border-bottom: 1px solid #eee;
                }}
                .invoice-detail:last-child {{
                    border-bottom: none;
                    font-weight: bold;
                    font-size: 1.2em;
                    color: #667eea;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .button-secondary {{
                    background: #10b981;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="{url_for('static', filename='uploads/logos/budgee_family_logo_trsp.png', _external=True)}" alt="Budgee Family" width="120" style="display: block; margin: 0 auto 20px auto;">
                    <h1>{title}</h1>
                </div>
                <div class="content">
                    <p>{greeting}</p>

                    <p>{thanks_payment}</p>

                    <div class="invoice-box">
                        <div class="invoice-detail">
                            <span>{invoice_num_label}</span>
                            <span><strong>{invoice_number}</strong></span>
                        </div>
                        <div class="invoice-detail">
                            <span>{date_label}</span>
                            <span>{invoice_date_str}</span>
                        </div>
                        <div class="invoice-detail">
                            <span>{amount_label}</span>
                            <span>{amount_paid:.2f} {currency_symbol}</span>
                        </div>
                    </div>

                    <p>{download_title}</p>

                    <div style="text-align: center;">
                        <a href="{invoice_pdf_url}" class="button">
                            {button_download}
                        </a>
                        <br>
                        <a href="{hosted_invoice_url}" class="button button-secondary">
                            {button_view}
                        </a>
                    </div>

                    <p>{auto_generated}</p>

                    <p>{thanks_closing}</p>

                    <p>{closing}</p>
                </div>
                <div class="footer">
                    <p>{footer_note}</p>
                    <p>{footer_question}</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        {title}

        {greeting}

        {thanks_payment.replace('<strong>', '').replace('</strong>', '')}

        {'Invoice details:' if lang == 'en' else 'Détails de la facture :'}
        - {invoice_num_label.replace(':', '')} : {invoice_number}
        - {date_label.replace(':', '')} : {invoice_date_str}
        - {amount_label.replace(':', '')} : {amount_paid:.2f} {currency_symbol}

        {button_download} :
        {invoice_pdf_url}

        {button_view} :
        {hosted_invoice_url}

        {auto_generated}

        {thanks_closing}

        {closing.replace('<br>', '')}
        """

        msg = Message(
            subject=subject,
            sender=os.getenv('MAIL_DEFAULT_SENDER', 'noreply@budgeefamily.com'),
            recipients=[user.email],
            body=text_body,
            html=html_body
        )

        mail.send(msg)
        return True

    except Exception as e:
        print(f"Erreur lors de l'envoi de la facture par email : {e}")
        return False


def send_notification_email(user, notification):
    """Envoie un email de notification à l'utilisateur"""
    try:
        # Ne pas envoyer d'email si l'utilisateur n'a pas activé les notifications par email
        if not user.email_notifications:
            return False

        lang = user.language or 'fr'

        # Définir l'icône et la couleur selon le type de notification
        notification_types = {
            'subscription_added': {'icon': '🔔', 'color': '#10b981'},
            'credit_added': {'icon': '💳', 'color': '#6366f1'},
            'revenue_added': {'icon': '💰', 'color': '#10b981'},
            'upgrade': {'icon': '⭐', 'color': '#f59e0b'},
            'downgrade': {'icon': '⬇️', 'color': '#ef4444'},
            'payment_failed': {'icon': '❌', 'color': '#ef4444'},
            'renewal': {'icon': '🔄', 'color': '#3b82f6'},
            'expiry': {'icon': '⚠️', 'color': '#f59e0b'},
            'daily_update': {'icon': '⚙️', 'color': '#3b82f6'},
            'reminder_appointment_10days': {'icon': '🔔', 'color': '#f59e0b'},
            'reminder_appointment_2days': {'icon': '⏰', 'color': '#ef4444'},
        }

        notif_info = notification_types.get(notification.type, {'icon': '🔔', 'color': '#6366f1'})

        # Contenu selon la langue
        if lang == 'en':
            title_notif = 'New notification'
            greeting = f'Hello {user.first_name or user.email},'
            button_dashboard = 'View my dashboard'
            preferences_note = f'You are receiving this email because you have enabled email notifications in your preferences. You can disable this option anytime from your <a href="{url_for(\'auth.profile\', _external=True)}">profile</a>.'
            footer_title = 'Smart subscription manager'
        else:
            title_notif = 'Nouvelle notification'
            greeting = f'Bonjour {user.first_name or user.email},'
            button_dashboard = 'Voir mon tableau de bord'
            preferences_note = f'Vous recevez cet email car vous avez activé les notifications par email dans vos préférences. Vous pouvez désactiver cette option à tout moment depuis votre <a href="{url_for(\'auth.profile\', _external=True)}">profil</a>.'
            footer_title = 'Gestionnaire d\'abonnements intelligent'

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                    background-color: #f8f9fa;
                }}
                .container {{
                    max-width: 600px;
                    margin: 20px auto;
                    background-color: #ffffff;
                    border-radius: 15px;
                    overflow: hidden;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, {notif_info['color']} 0%, {notif_info['color']}dd 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                    font-weight: bold;
                }}
                .content {{
                    padding: 30px;
                }}
                .notification-box {{
                    background: #f8f9fa;
                    border-left: 4px solid {notif_info['color']};
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                }}
                .notification-box h3 {{
                    color: {notif_info['color']};
                    margin-top: 0;
                }}
                .notification-box p {{
                    white-space: pre-line;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background: {notif_info['color']};
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                    margin: 20px 0;
                    font-weight: 600;
                }}
                .footer {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    color: #6b7280;
                    font-size: 12px;
                    border-top: 1px solid #e5e7eb;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="{url_for('static', filename='uploads/logos/budgee_family_logo_trsp.png', _external=True)}" alt="Budgee Family" width="120" style="display: block; margin: 0 auto 20px auto;">
                    <h1>{notif_info['icon']} {title_notif}</h1>
                </div>
                <div class="content">
                    <p>{greeting}</p>

                    <div class="notification-box">
                        <h3>{notification.title}</h3>
                        <p>{notification.message}</p>
                    </div>

                    <div style="text-align: center;">
                        <a href="{url_for('main.dashboard', _external=True)}" class="button" style="color: white;">
                            {button_dashboard}
                        </a>
                    </div>

                    <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
                        <em>{preferences_note}</em>
                    </p>
                </div>
                <div class="footer">
                    <p><strong>Budgee Family</strong> - {footer_title}</p>
                    <p style="margin-top: 8px; color: #9ca3af;">© {datetime.now().year} Budgee Family. {'All rights reserved.' if lang == 'en' else 'Tous droits réservés.'}</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        {notif_info['icon']} {title_notif} - Budgee Family

        {greeting}

        {notification.title}

        {notification.message}

        {button_dashboard} : {url_for('main.dashboard', _external=True)}

        ---
        {preferences_note.replace('<a href="', '').replace('">', ' : ').replace('</a>', '').replace('<em>', '').replace('</em>', '')}

        Budgee Family - {footer_title}
        © {datetime.now().year} Budgee Family. {'All rights reserved.' if lang == 'en' else 'Tous droits réservés.'}
        """

        msg = Message(
            subject=f'{notif_info["icon"]} {notification.title} - Budgee Family',
            sender=os.getenv('MAIL_DEFAULT_SENDER', 'noreply@budgeefamily.com'),
            recipients=[user.email],
            body=text_body,
            html=html_body
        )

        mail.send(msg)
        return True

    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email de notification : {e}")
        return False
