from flask import url_for, render_template_string
from flask_mail import Message, Mail
from app import mail
import os
import stripe

def send_verification_email(user):
    """Envoie un email de vérification à l'utilisateur"""
    token = user.generate_verification_token()

    verification_url = url_for('auth.verify_email', token=token, _external=True)

    # Contenu sur l'essai Premium (seulement si trial_start_date est défini)
    trial_content_html = ""
    trial_content_text = ""
    if user.trial_start_date:
        trial_content_html = """
                <p style="color: #28a745; font-weight: bold;">🎁 Bonus : Vous bénéficiez de 7 jours d'essai Premium gratuit !</p>

                <p>Avec Subly Cloud Premium, vous pouvez :</p>
                <ul>
                    <li>Gérer un nombre illimité d'abonnements</li>
                    <li>Créer des catégories et services personnalisés</li>
                    <li>Accéder aux statistiques avancées</li>
                    <li>Exporter vos données</li>
                </ul>
"""
        trial_content_text = """
    🎁 Bonus : Vous bénéficiez de 7 jours d'essai Premium gratuit !

    Avec Subly Cloud Premium, vous pouvez :
    - Gérer un nombre illimité d'abonnements
    - Créer des catégories et services personnalisés
    - Accéder aux statistiques avancées
    - Exporter vos données
"""

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
                <h1>Bienvenue sur Subly Cloud !</h1>
            </div>
            <div class="content">
                <p>Bonjour {user.first_name or 'cher utilisateur'},</p>

                <p>Merci de vous être inscrit sur <strong>Subly Cloud</strong>, votre gestionnaire d'abonnements intelligent !</p>

                <p>Pour commencer à utiliser toutes nos fonctionnalités, veuillez confirmer votre adresse email en cliquant sur le bouton ci-dessous :</p>

                <div style="text-align: center;">
                    <a href="{verification_url}" class="button">Confirmer mon adresse email</a>
                </div>

                {trial_content_html}

                <p>Si vous n'avez pas créé de compte sur Subly Cloud, vous pouvez ignorer cet email.</p>

                <p>À bientôt,<br>L'équipe Subly Cloud</p>
            </div>
            <div class="footer">
                <p>Cet email a été envoyé par Subly Cloud</p>
                <p>Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :<br>
                {verification_url}</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Bienvenue sur Subly Cloud !

    Bonjour {user.first_name or 'cher utilisateur'},

    Merci de vous être inscrit sur Subly Cloud, votre gestionnaire d'abonnements intelligent !

    Pour commencer à utiliser toutes nos fonctionnalités, veuillez confirmer votre adresse email en cliquant sur ce lien :
    {verification_url}
    {trial_content_text}
    Si vous n'avez pas créé de compte sur Subly Cloud, vous pouvez ignorer cet email.

    À bientôt,
    L'équipe Subly Cloud
    """

    msg = Message(
        subject='Bienvenue sur Subly Cloud - Confirmez votre email',
        sender=os.getenv('MAIL_DEFAULT_SENDER', 'noreply@subly.cloud'),
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

                <p>Cordialement,<br>L'équipe Subly Cloud</p>
            </div>
            <div class="footer">
                <p>Cet email a été envoyé par Subly Cloud</p>
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
    L'équipe Subly Cloud
    """

    msg = Message(
        subject='Confirmation de rétrogradation - Subly Cloud',
        sender=os.getenv('MAIL_DEFAULT_SENDER', 'noreply@subly.cloud'),
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
    """Envoie un email de confirmation de passage à un plan Premium"""

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
            .success-box {{
                background: #d1fae5;
                border-left: 4px solid #10b981;
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
                <h1>🎉 Bienvenue chez Premium !</h1>
            </div>
            <div class="content">
                <p>Bonjour {user.first_name or user.email},</p>

                <p>Félicitations ! Votre compte a été mis à niveau vers le plan <strong>{new_plan_name}</strong>.</p>

                <div class="success-box">
                    <h3>Vous bénéficiez maintenant de :</h3>
                    <ul>
                        <li>✅ Abonnements illimités</li>
                        <li>✅ Catégories personnalisées illimitées</li>
                        <li>✅ Services personnalisés illimités</li>
                        <li>✅ Plans de services illimités</li>
                        <li>✅ Statistiques avancées</li>
                        <li>✅ Export de données</li>
                        <li>✅ Support prioritaire</li>
                    </ul>
                </div>

                <p>Profitez pleinement de toutes les fonctionnalités Premium pour gérer vos abonnements comme un pro !</p>

                <div style="text-align: center;">
                    <a href="{url_for('main.dashboard', _external=True)}" class="button">Accéder à mon tableau de bord</a>
                </div>

                <p>Merci de votre confiance !</p>

                <p>Cordialement,<br>L'équipe Subly Cloud</p>
            </div>
            <div class="footer">
                <p>Cet email a été envoyé par Subly Cloud</p>
                <p>Si vous avez des questions, n'hésitez pas à nous contacter.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    🎉 Bienvenue chez Premium !

    Bonjour {user.first_name or user.email},

    Félicitations ! Votre compte a été mis à niveau vers le plan {new_plan_name}.

    Vous bénéficiez maintenant de :
    ✅ Abonnements illimités
    ✅ Catégories personnalisées illimitées
    ✅ Services personnalisés illimités
    ✅ Plans de services illimités
    ✅ Statistiques avancées
    ✅ Export de données
    ✅ Support prioritaire

    Profitez pleinement de toutes les fonctionnalités Premium pour gérer vos abonnements comme un pro !

    Accéder à mon tableau de bord : {url_for('main.dashboard', _external=True)}

    Merci de votre confiance !

    Cordialement,
    L'équipe Subly Cloud
    """

    msg = Message(
        subject=f'Bienvenue sur {new_plan_name} - Subly Cloud',
        sender=os.getenv('MAIL_DEFAULT_SENDER', 'noreply@subly.cloud'),
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
                    <h1>📄 Votre facture Subly Cloud</h1>
                </div>
                <div class="content">
                    <p>Bonjour {user.first_name or user.email},</p>

                    <p>Merci pour votre paiement ! Voici votre facture pour votre abonnement <strong>Subly Cloud Premium</strong>.</p>

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

                    <p>Cordialement,<br>L'équipe Subly Cloud</p>
                </div>
                <div class="footer">
                    <p>Cet email a été envoyé par Subly Cloud</p>
                    <p>Si vous avez des questions concernant votre facture, n'hésitez pas à nous contacter.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Votre facture Subly Cloud

        Bonjour {user.first_name or user.email},

        Merci pour votre paiement ! Voici votre facture pour votre abonnement Subly Cloud Premium.

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
        L'équipe Subly Cloud
        """

        msg = Message(
            subject=f'Votre facture Subly Cloud #{invoice_number}',
            sender=os.getenv('MAIL_DEFAULT_SENDER', 'noreply@subly.cloud'),
            recipients=[user.email],
            body=text_body,
            html=html_body
        )

        mail.send(msg)
        return True

    except Exception as e:
        print(f"Erreur lors de l'envoi de la facture par email : {e}")
        return False
