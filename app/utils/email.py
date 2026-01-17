from flask import url_for, render_template_string
from flask_mail import Message, Mail
from app import mail
import os
import stripe
from datetime import datetime

def send_verification_email(user):
    """Envoie un email de vérification à l'utilisateur"""
    token = user.generate_verification_token()

    verification_url = url_for('auth.verify_email', token=token, _external=True)

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
                <h1>Bienvenue sur Budgee Family !</h1>
            </div>
            <div class="content">
                <p>Bonjour {user.first_name or 'cher utilisateur'},</p>

                <p>Merci de vous être inscrit sur <strong>Budgee Family</strong>, votre gestionnaire d'abonnements intelligent !</p>

                <p>Pour commencer à utiliser toutes nos fonctionnalités, veuillez confirmer votre adresse email en cliquant sur le bouton ci-dessous :</p>

                <div style="text-align: center;">
                    <a href="{verification_url}" class="button">Confirmer mon adresse email</a>
                </div>

                <p>Si vous n'avez pas créé de compte sur Budgee Family, vous pouvez ignorer cet email.</p>

                <p>À bientôt,<br>L'équipe Budgee Family</p>
            </div>
            <div class="footer">
                <p>Cet email a été envoyé par Budgee Family</p>
                <p>Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :<br>
                {verification_url}</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Bienvenue sur Budgee Family !

    Bonjour {user.first_name or 'cher utilisateur'},

    Merci de vous être inscrit sur Budgee Family, votre gestionnaire d'abonnements intelligent !

    Pour commencer à utiliser toutes nos fonctionnalités, veuillez confirmer votre adresse email en cliquant sur ce lien :
    {verification_url}

    Si vous n'avez pas créé de compte sur Budgee Family, vous pouvez ignorer cet email.

    À bientôt,
    L'équipe Budgee Family
    """

    msg = Message(
        subject='Bienvenue sur Budgee Family - Confirmez votre email',
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
                <h1>Rétrogradation confirmée</h1>
            </div>
            <div class="content">
                <p>Bonjour {user.first_name or user.email},</p>

                <p>Nous vous confirmons que votre compte a été rétrogradé du plan <strong>{old_plan_name}</strong> vers le <strong>plan gratuit</strong>.</p>

                <div class="info-box">
                    <h3>Votre plan gratuit comprend :</h3>
                    <ul>
                        <li>Jusqu'à 5 abonnements</li>
                        <li>Jusqu'à 5 catégories personnalisées</li>
                        <li>Jusqu'à 5 services personnalisés</li>
                        <li>Jusqu'à 10 plans de services personnalisés</li>
                        <li>Statistiques de base</li>
                        <li>Notifications d'échéance</li>
                    </ul>
                </div>

                <p>Toutes vos données ont été conservées. Si vous dépassez les limites du plan gratuit, vous ne pourrez simplement pas créer de nouveaux éléments jusqu'à ce que vous en supprimiez ou que vous repassiez à Premium.</p>

                <p><strong>Vous pouvez repasser à Premium à tout moment !</strong></p>

                <div style="text-align: center;">
                    <a href="{url_for('main.pricing', _external=True)}" class="button">Voir les plans Premium</a>
                </div>

                <p>Nous espérons vous revoir bientôt parmi nos utilisateurs Premium.</p>

                <p>Cordialement,<br>L'équipe Budgee Family</p>
            </div>
            <div class="footer">
                <p>Cet email a été envoyé par Budgee Family</p>
                <p>Si vous n'avez pas effectué cette action, veuillez nous contacter immédiatement.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Rétrogradation confirmée

    Bonjour {user.first_name or user.email},

    Nous vous confirmons que votre compte a été rétrogradé du plan {old_plan_name} vers le plan gratuit.

    Votre plan gratuit comprend :
    - Jusqu'à 5 abonnements
    - Jusqu'à 5 catégories personnalisées
    - Jusqu'à 5 services personnalisés
    - Jusqu'à 10 plans de services personnalisés
    - Statistiques de base
    - Notifications d'échéance

    Toutes vos données ont été conservées. Si vous dépassez les limites du plan gratuit, vous ne pourrez simplement pas créer de nouveaux éléments jusqu'à ce que vous en supprimiez ou que vous repassiez à Premium.

    Vous pouvez repasser à Premium à tout moment !
    Voir les plans : {url_for('main.pricing', _external=True)}

    Nous espérons vous revoir bientôt parmi nos utilisateurs Premium.

    Cordialement,
    L'équipe Budgee Family
    """

    msg = Message(
        subject='Confirmation de rétrogradation - Budgee Family',
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

    # Symbole de devise
    currency_symbols = {
        'EUR': '€', 'USD': '$', 'GBP': '£', 'CHF': 'CHF',
        'CAD': '$', 'AUD': '$', 'JPY': '¥', 'CNY': '¥',
        'INR': '₹', 'BRL': 'R$', 'MXN': '$', 'ZAR': 'R'
    }
    currency_symbol = currency_symbols.get(plan.currency, plan.currency) if plan else '€'

    # Traduction de la période de facturation
    billing_period_fr = {
        'monthly': 'mensuel',
        'yearly': 'annuel',
        'lifetime': 'à vie'
    }
    period_text = billing_period_fr.get(plan.billing_period, plan.billing_period) if plan else 'mensuel'

    # Prix formaté
    price_text = f"{plan.price:.2f} {currency_symbol}" if plan else "N/A"

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
                <h1>🎉 Bienvenue chez Premium !</h1>
                <p>Votre abonnement a été activé avec succès</p>
            </div>

            <div class="content">
                <h2>Bonjour {user.first_name or user.email},</h2>

                <p>Félicitations et bienvenue dans la famille <strong>Budgee Family Premium</strong> !</p>

                <p>Nous sommes ravis de vous compter parmi nos membres Premium. Votre paiement a été traité avec succès et votre abonnement est désormais actif.</p>

                <div class="subscription-summary">
                    <h3>📋 Récapitulatif de votre abonnement</h3>
                    <div class="summary-item">
                        <span class="summary-label">Plan souscrit</span>
                        <span class="summary-value">{new_plan_name}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Période de facturation</span>
                        <span class="summary-value">{period_text.capitalize()}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Montant</span>
                        <span class="summary-value">{price_text}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Date d'activation</span>
                        <span class="summary-value">{datetime.now().strftime('%d/%m/%Y')}</span>
                    </div>
                </div>

                <p><strong>Avec votre plan Premium, vous bénéficiez de :</strong></p>

                <div class="feature-list">
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
                    </div>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{url_for('main.dashboard', _external=True)}" class="button" style="color: white;">
                        🚀 Accéder à mon tableau de bord
                    </a>
                </div>

                <p>Vous recevrez également votre facture dans un email séparé. Vous pourrez la retrouver à tout moment dans votre espace client.</p>

                <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
                    <em>Merci de votre confiance ! Nous sommes là pour vous accompagner dans la gestion de vos abonnements.</em>
                </p>
            </div>

            <div class="footer">
                <p><strong>Budgee Family</strong> - Gestionnaire d'abonnements intelligent</p>
                <p style="margin-top: 8px;">
                    <a href="https://budgeefamily.com">Site web</a> •
                    <a href="https://budgeefamily.com/contact">Contact</a> •
                    <a href="https://budgeefamily.com/mentions-legales">Mentions légales</a>
                </p>
                <p style="margin-top: 15px; font-size: 12px; color: #9ca3af;">
                    © {datetime.now().year} Budgee Family. Tous droits réservés.
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    🎉 Bienvenue chez Premium !

    Bonjour {user.first_name or user.email},

    Félicitations et bienvenue dans la famille Budgee Family Premium !

    Nous sommes ravis de vous compter parmi nos membres Premium. Votre paiement a été traité avec succès et votre abonnement est désormais actif.

    📋 RÉCAPITULATIF DE VOTRE ABONNEMENT

    Plan souscrit : {new_plan_name}
    Période de facturation : {period_text.capitalize()}
    Montant : {price_text}
    Date d'activation : {datetime.now().strftime('%d/%m/%Y')}

    AVEC VOTRE PLAN PREMIUM, VOUS BÉNÉFICIEZ DE :

    ✓ Abonnements illimités - Ajoutez autant d'abonnements que vous le souhaitez
    ✓ Catégories personnalisées illimitées - Organisez vos abonnements à votre façon
    ✓ Services personnalisés illimités - Créez vos propres services
    ✓ Plans de services illimités - Gérez tous vos plans tarifaires
    ✓ Statistiques avancées - Analysez vos dépenses en détail
    ✓ Export de données - Téléchargez vos données quand vous voulez
    ✓ Support prioritaire - Une assistance rapide et personnalisée

    🚀 Accéder à mon tableau de bord : {url_for('main.dashboard', _external=True)}

    Vous recevrez également votre facture dans un email séparé. Vous pourrez la retrouver à tout moment dans votre espace client.

    Merci de votre confiance ! Nous sommes là pour vous accompagner dans la gestion de vos abonnements.

    ---
    Budgee Family - Gestionnaire d'abonnements intelligent
    Site web : https://budgeefamily.com
    Contact : https://budgeefamily.com/contact

    © {datetime.now().year} Budgee Family. Tous droits réservés.
    """

    msg = Message(
        subject=f'✓ Bienvenue sur {new_plan_name} - Budgee Family',
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


def send_contact_confirmation_email(name, email):
    """Envoie un email de confirmation après l'envoi d'un message via le formulaire de contact"""

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
                <h1>Message bien reçu !</h1>
                <p>Merci de nous avoir contactés</p>
            </div>

            <div class="content">
                <h2>Bonjour {name},</h2>

                <p>Nous avons bien reçu votre message et nous vous remercions de l'intérêt que vous portez à <strong>Budgee Family</strong>.</p>

                <div class="info-box">
                    <p><strong>✓ Votre demande a été enregistrée</strong></p>
                    <p style="margin-top: 10px;">Notre équipe reviendra vers vous dans les <strong>24 à 48 heures</strong>.</p>
                </div>

                <p>En attendant notre réponse, saviez-vous que Budgee Family vous permet de :</p>

                <div class="feature-list">
                    <div class="feature-item">
                        ✓ <strong>Gérer tous vos abonnements</strong> en un seul endroit
                    </div>
                    <div class="feature-item">
                        ✓ <strong>Recevoir des notifications</strong> avant chaque renouvellement
                    </div>
                    <div class="feature-item">
                        ✓ <strong>Visualiser vos dépenses</strong> mensuelles en temps réel
                    </div>
                    <div class="feature-item">
                        ✓ <strong>Organiser par catégories</strong> avec logos personnalisés
                    </div>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://budgeefamily.com" class="button" style="color: white;">
                        🚀 Découvrir Budgee Family
                    </a>
                </div>

                <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
                    <em>Cet email confirme la réception de votre message. Vous n'avez aucune action à effectuer.</em>
                </p>
            </div>

            <div class="footer">
                <p><strong>Budgee Family</strong> - Gestionnaire d'abonnements intelligent</p>
                <p style="margin-top: 8px;">
                    <a href="https://budgeefamily.com">Site web</a> •
                    <a href="https://budgeefamily.com/contact">Contact</a> •
                    <a href="https://budgeefamily.com/mentions-legales">Mentions légales</a>
                </p>
                <p style="margin-top: 15px; font-size: 12px; color: #9ca3af;">
                    © {datetime.now().year} Budgee Family. Tous droits réservés.
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Message bien reçu !

    Bonjour {name},

    Nous avons bien reçu votre message et nous vous remercions de l'intérêt que vous portez à Budgee Family.

    ✓ Votre demande a été enregistrée
    Notre équipe reviendra vers vous dans les 24 à 48 heures.

    En attendant notre réponse, saviez-vous que Budgee Family vous permet de :
    ✓ Gérer tous vos abonnements en un seul endroit
    ✓ Recevoir des notifications avant chaque renouvellement
    ✓ Visualiser vos dépenses mensuelles en temps réel
    ✓ Organiser par catégories avec logos personnalisés

    Découvrir Budgee Family : https://budgeefamily.com

    Cet email confirme la réception de votre message. Vous n'avez aucune action à effectuer.

    ---
    Budgee Family - Gestionnaire d'abonnements intelligent
    Site web : https://budgeefamily.com
    Contact : https://budgeefamily.com/contact

    © {datetime.now().year} Budgee Family. Tous droits réservés.
    """

    msg = Message(
        subject='✓ Message reçu - Budgee Family',
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
    billing_period_fr = {
        'monthly': 'mensuel',
        'yearly': 'annuel',
        'lifetime': 'à vie'
    }
    period_text = billing_period_fr.get(plan.billing_period, plan.billing_period) if plan else 'gratuit'

    # Prix formaté
    price_text = f"{plan.price:.2f} {currency_symbol}" if plan and plan.price > 0 else "Gratuit"

    # Nom du plan
    plan_name = plan.name if plan else "Free"

    # Contenu spécifique selon le type de plan
    if is_free_plan:
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
                <h1>🎉 Bienvenue sur Budgee Family !</h1>
                <p>Votre compte a été créé avec succès</p>
            </div>

            <div class="content">
                <h2>Bonjour {user.first_name or user.email},</h2>

                <p>Merci de vous être inscrit sur <strong>Budgee Family</strong>, votre gestionnaire d'abonnements intelligent !</p>

                <p>Nous sommes ravis de vous accueillir et vous souhaitons la bienvenue dans notre communauté.</p>

                <div class="subscription-summary">
                    <h3>📋 Récapitulatif de votre abonnement</h3>
                    <div class="summary-item">
                        <span class="summary-label">Plan souscrit</span>
                        <span class="summary-value">{plan_name}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Type d'abonnement</span>
                        <span class="summary-value">{period_text.capitalize()}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Tarif</span>
                        <span class="summary-value">{price_text}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Date d'inscription</span>
                        <span class="summary-value">{datetime.now().strftime('%d/%m/%Y')}</span>
                    </div>
                </div>

                <p><strong>Avec votre plan {plan_name}, vous bénéficiez de :</strong></p>

                <div class="feature-list">
{features_html}
                </div>

{upgrade_section_html}

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{url_for('main.dashboard', _external=True)}" class="button" style="color: white;">
                        🚀 Accéder à mon tableau de bord
                    </a>
                </div>

                <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
                    <em>Merci de votre confiance ! Nous sommes là pour vous accompagner dans la gestion de vos abonnements.</em>
                </p>
            </div>

            <div class="footer">
                <p><strong>Budgee Family</strong> - Gestionnaire d'abonnements intelligent</p>
                <p style="margin-top: 8px;">
                    <a href="https://budgeefamily.com">Site web</a> •
                    <a href="https://budgeefamily.com/contact">Contact</a> •
                    <a href="https://budgeefamily.com/mentions-legales">Mentions légales</a>
                </p>
                <p style="margin-top: 15px; font-size: 12px; color: #9ca3af;">
                    © {datetime.now().year} Budgee Family. Tous droits réservés.
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    🎉 Bienvenue sur Budgee Family !

    Bonjour {user.first_name or user.email},

    Merci de vous être inscrit sur Budgee Family, votre gestionnaire d'abonnements intelligent !

    Nous sommes ravis de vous accueillir et vous souhaitons la bienvenue dans notre communauté.

    📋 RÉCAPITULATIF DE VOTRE ABONNEMENT

    Plan souscrit : {plan_name}
    Type d'abonnement : {period_text.capitalize()}
    Tarif : {price_text}
    Date d'inscription : {datetime.now().strftime('%d/%m/%Y')}

    AVEC VOTRE PLAN {plan_name.upper()}, VOUS BÉNÉFICIEZ DE :

    {features_text}
{upgrade_section_text}

    🚀 Accéder à mon tableau de bord : {url_for('main.dashboard', _external=True)}

    Merci de votre confiance ! Nous sommes là pour vous accompagner dans la gestion de vos abonnements.

    ---
    Budgee Family - Gestionnaire d'abonnements intelligent
    Site web : https://budgeefamily.com
    Contact : https://budgeefamily.com/contact

    © {datetime.now().year} Budgee Family. Tous droits réservés.
    """

    msg = Message(
        subject=f'✓ Bienvenue sur Budgee Family - Plan {plan_name}',
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
                    <h1>📄 Votre facture Budgee Family</h1>
                </div>
                <div class="content">
                    <p>Bonjour {user.first_name or user.email},</p>

                    <p>Merci pour votre paiement ! Voici votre facture pour votre abonnement <strong>Budgee Family Premium</strong>.</p>

                    <div class="invoice-box">
                        <div class="invoice-detail">
                            <span>Numéro de facture :</span>
                            <span><strong>{invoice_number}</strong></span>
                        </div>
                        <div class="invoice-detail">
                            <span>Date :</span>
                            <span>{invoice_date_str}</span>
                        </div>
                        <div class="invoice-detail">
                            <span>Montant payé :</span>
                            <span>{amount_paid:.2f} {currency_symbol}</span>
                        </div>
                    </div>

                    <p><strong>Télécharger votre facture :</strong></p>

                    <div style="text-align: center;">
                        <a href="{invoice_pdf_url}" class="button">
                            📥 Télécharger la facture PDF
                        </a>
                        <br>
                        <a href="{hosted_invoice_url}" class="button button-secondary">
                            👁️ Voir la facture en ligne
                        </a>
                    </div>

                    <p>Cette facture est générée automatiquement pour votre abonnement Premium. Vous pouvez la télécharger et la conserver pour vos dossiers.</p>

                    <p>Merci de votre confiance !</p>

                    <p>Cordialement,<br>L'équipe Budgee Family</p>
                </div>
                <div class="footer">
                    <p>Cet email a été envoyé par Budgee Family</p>
                    <p>Si vous avez des questions concernant votre facture, n'hésitez pas à nous contacter.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Votre facture Budgee Family

        Bonjour {user.first_name or user.email},

        Merci pour votre paiement ! Voici votre facture pour votre abonnement Budgee Family Premium.

        Détails de la facture :
        - Numéro : {invoice_number}
        - Date : {invoice_date_str}
        - Montant payé : {amount_paid:.2f} {currency_symbol}

        Télécharger votre facture PDF :
        {invoice_pdf_url}

        Voir la facture en ligne :
        {hosted_invoice_url}

        Cette facture est générée automatiquement pour votre abonnement Premium.
        Vous pouvez la télécharger et la conserver pour vos dossiers.

        Merci de votre confiance !

        Cordialement,
        L'équipe Budgee Family
        """

        msg = Message(
            subject=f'Votre facture Budgee Family #{invoice_number}',
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
        }

        notif_info = notification_types.get(notification.type, {'icon': '🔔', 'color': '#6366f1'})

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
                    <h1>{notif_info['icon']} Nouvelle notification</h1>
                </div>
                <div class="content">
                    <p>Bonjour {user.first_name or user.email},</p>

                    <div class="notification-box">
                        <h3>{notification.title}</h3>
                        <p>{notification.message}</p>
                    </div>

                    <div style="text-align: center;">
                        <a href="{url_for('main.dashboard', _external=True)}" class="button" style="color: white;">
                            Voir mon tableau de bord
                        </a>
                    </div>

                    <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
                        <em>Vous recevez cet email car vous avez activé les notifications par email dans vos préférences. Vous pouvez désactiver cette option à tout moment depuis votre <a href="{url_for('auth.profile', _external=True)}">profil</a>.</em>
                    </p>
                </div>
                <div class="footer">
                    <p><strong>Budgee Family</strong> - Gestionnaire d'abonnements intelligent</p>
                    <p style="margin-top: 8px; color: #9ca3af;">© {datetime.now().year} Budgee Family. Tous droits réservés.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        {notif_info['icon']} Nouvelle notification - Budgee Family

        Bonjour {user.first_name or user.email},

        {notification.title}

        {notification.message}

        Voir mon tableau de bord : {url_for('main.dashboard', _external=True)}

        ---
        Vous recevez cet email car vous avez activé les notifications par email dans vos préférences.
        Vous pouvez désactiver cette option à tout moment depuis votre profil : {url_for('auth.profile', _external=True)}

        Budgee Family - Gestionnaire d'abonnements intelligent
        © {datetime.now().year} Budgee Family. Tous droits réservés.
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
