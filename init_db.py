#!/usr/bin/env python3
"""
Script d'initialisation de la base de données
Crée les tables et ajoute les données de base (plans, catégories)
"""

from app import create_app, db
from app.models import Plan, Category, Service, ServicePlan

def init_database():
    app = create_app()

    with app.app_context():
        print("Création des tables...")
        db.create_all()
        print("Tables créées avec succès !")

        # Vérifier si les plans existent déjà
        if Plan.query.count() == 0:
            print("\nCréation des plans...")

            # Plan gratuit
            free_plan = Plan(
                name='Free',
                price=0.0,
                currency='EUR',
                billing_period='monthly',
                max_subscriptions=5,
                description='Plan gratuit avec un maximum de 5 abonnements',
                features=[
                    '5 abonnements maximum',
                    'Accès aux catégories par défaut',
                    'Statistiques détaillées',
                    'Notifications de renouvellement',
                    'Support communautaire'
                ],
                is_active=True
            )

            # Plan Premium Mensuel
            premium_plan = Plan(
                name='Premium',
                price=4.99,
                currency='EUR',
                billing_period='monthly',
                max_subscriptions=None,
                description='Plan Premium mensuel avec abonnements illimités et catégories personnalisées',
                features=[
                    'Abonnements illimités',
                    'Catégories personnalisées (logos, couleurs, icônes)',
                    'Accès aux catégories par défaut',
                    'Statistiques avancées',
                    'Notifications personnalisables',
                    'Support prioritaire',
                    'Export des données (PDF, CSV)',
                    'Accès anticipé aux nouvelles fonctionnalités'
                ],
                is_active=True
            )

            # Plan Premium Annuel
            premium_annual_plan = Plan(
                name='Premium Annual',
                price=49.99,
                currency='EUR',
                billing_period='yearly',
                max_subscriptions=None,
                description='Plan Premium annuel avec abonnements illimités et catégories personnalisées',
                features=[
                    'Abonnements illimités',
                    'Catégories personnalisées (logos, couleurs, icônes)',
                    'Accès aux catégories par défaut',
                    'Statistiques avancées',
                    'Notifications personnalisables',
                    'Support prioritaire',
                    'Export des données (PDF, CSV)',
                    'Accès anticipé aux nouvelles fonctionnalités',
                    '2 mois gratuits (économie de 10€)'
                ],
                is_active=True
            )

            db.session.add(free_plan)
            db.session.add(premium_plan)
            db.session.add(premium_annual_plan)
            db.session.commit()
            print("Plans créés avec succès !")
        else:
            print("\nLes plans existent déjà.")

        # Vérifier si les catégories existent déjà
        if Category.query.count() == 0:
            print("\nCréation des catégories par défaut...")

            categories = [
                {
                    'name': 'Streaming Vidéo',
                    'description': 'Services de streaming vidéo et films',
                    'color': '#E50914',
                    'icon': 'fas fa-film'
                },
                {
                    'name': 'Streaming Audio',
                    'description': 'Services de musique et podcasts',
                    'color': '#1DB954',
                    'icon': 'fas fa-music'
                },
                {
                    'name': 'Cloud & Stockage',
                    'description': 'Services de stockage en ligne',
                    'color': '#4285F4',
                    'icon': 'fas fa-cloud'
                },
                {
                    'name': 'Productivité',
                    'description': 'Outils de productivité et bureautique',
                    'color': '#FF6900',
                    'icon': 'fas fa-briefcase'
                },
                {
                    'name': 'Développement',
                    'description': 'Outils pour développeurs',
                    'color': '#6366F1',
                    'icon': 'fas fa-code'
                },
                {
                    'name': 'Design & Créatif',
                    'description': 'Outils de design et création',
                    'color': '#FF0080',
                    'icon': 'fas fa-palette'
                },
                {
                    'name': 'Fitness & Santé',
                    'description': 'Applications de fitness et santé',
                    'color': '#00C851',
                    'icon': 'fas fa-heartbeat'
                },
                {
                    'name': 'Gaming',
                    'description': 'Services de jeux et gaming',
                    'color': '#9146FF',
                    'icon': 'fas fa-gamepad'
                },
                {
                    'name': 'Actualités & Médias',
                    'description': 'Abonnements à des journaux et médias',
                    'color': '#1E1E1E',
                    'icon': 'fas fa-newspaper'
                },
                {
                    'name': 'Autre',
                    'description': 'Autres types d\'abonnements',
                    'color': '#6C757D',
                    'icon': 'fas fa-ellipsis-h'
                }
            ]

            for cat_data in categories:
                category = Category(**cat_data)
                db.session.add(category)

            db.session.commit()
            print(f"{len(categories)} catégories créées avec succès !")
        else:
            print("\nLes catégories existent déjà.")

        # Vérifier si les services existent déjà
        if Service.query.count() == 0:
            print("\nCréation des services par défaut...")

            # Récupérer les catégories pour les associer
            video_category = Category.query.filter_by(name='Streaming Vidéo').first()
            audio_category = Category.query.filter_by(name='Streaming Audio').first()
            cloud_category = Category.query.filter_by(name='Cloud & Stockage').first()
            productivity_category = Category.query.filter_by(name='Productivité').first()
            design_category = Category.query.filter_by(name='Design & Créatif').first()

            services_data = []

            # Netflix
            netflix = Service(
                name='Netflix',
                description='Service de streaming vidéo',
                category_id=video_category.id if video_category else None,
                website_url='https://www.netflix.com',
                logo_url='/static/uploads/logos/netflix.png',
                is_active=True
            )
            db.session.add(netflix)
            db.session.flush()

            netflix_plans = [
                ServicePlan(service_id=netflix.id, name='Essentiel avec pub', amount=5.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=netflix.id, name='Standard', amount=13.49, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=netflix.id, name='Premium', amount=19.99, currency='EUR', billing_cycle='monthly')
            ]
            for plan in netflix_plans:
                db.session.add(plan)
            services_data.append(('Netflix', len(netflix_plans)))

            # Disney+
            disney = Service(
                name='Disney+',
                description='Service de streaming vidéo Disney, Pixar, Marvel, Star Wars',
                category_id=video_category.id if video_category else None,
                website_url='https://www.disneyplus.com',
                logo_url='/static/uploads/logos/disneyplus.png',
                is_active=True
            )
            db.session.add(disney)
            db.session.flush()

            disney_plans = [
                ServicePlan(service_id=disney.id, name='Standard avec pub', amount=5.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=disney.id, name='Standard', amount=8.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=disney.id, name='Premium', amount=11.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=disney.id, name='Standard', amount=89.90, currency='EUR', billing_cycle='yearly'),
                ServicePlan(service_id=disney.id, name='Premium', amount=119.90, currency='EUR', billing_cycle='yearly')
            ]
            for plan in disney_plans:
                db.session.add(plan)
            services_data.append(('Disney+', len(disney_plans)))

            # Prime Video
            prime = Service(
                name='Prime Video',
                description='Service de streaming vidéo Amazon',
                category_id=video_category.id if video_category else None,
                website_url='https://www.primevideo.com',
                logo_url='/static/uploads/logos/primevideo.png',
                is_active=True
            )
            db.session.add(prime)
            db.session.flush()

            prime_plans = [
                ServicePlan(service_id=prime.id, name='Prime Video', amount=6.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=prime.id, name='Amazon Prime', amount=69.90, currency='EUR', billing_cycle='yearly')
            ]
            for plan in prime_plans:
                db.session.add(plan)
            services_data.append(('Prime Video', len(prime_plans)))

            # Canal+
            canal = Service(
                name='Canal+',
                description='Chaîne de télévision française premium',
                category_id=video_category.id if video_category else None,
                website_url='https://www.canalplus.com',
                logo_url='/static/uploads/logos/canalplus.png',
                is_active=True
            )
            db.session.add(canal)
            db.session.flush()

            canal_plans = [
                ServicePlan(service_id=canal.id, name='Canal+', amount=24.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=canal.id, name='Canal+ Ciné Séries', amount=34.99, currency='EUR', billing_cycle='monthly')
            ]
            for plan in canal_plans:
                db.session.add(plan)
            services_data.append(('Canal+', len(canal_plans)))

            # Spotify
            spotify = Service(
                name='Spotify',
                description='Service de streaming audio et podcasts',
                category_id=audio_category.id if audio_category else None,
                website_url='https://www.spotify.com',
                logo_url='/static/uploads/logos/spotify.png',
                is_active=True
            )
            db.session.add(spotify)
            db.session.flush()

            spotify_plans = [
                ServicePlan(service_id=spotify.id, name='Individual', amount=10.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=spotify.id, name='Duo', amount=14.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=spotify.id, name='Family', amount=17.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=spotify.id, name='Student', amount=5.99, currency='EUR', billing_cycle='monthly')
            ]
            for plan in spotify_plans:
                db.session.add(plan)
            services_data.append(('Spotify', len(spotify_plans)))

            # Apple Music
            apple_music = Service(
                name='Apple Music',
                description='Service de streaming musical Apple',
                category_id=audio_category.id if audio_category else None,
                website_url='https://www.apple.com/apple-music',
                logo_url='/static/uploads/logos/applemusic.png',
                is_active=True
            )
            db.session.add(apple_music)
            db.session.flush()

            apple_music_plans = [
                ServicePlan(service_id=apple_music.id, name='Voice', amount=4.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=apple_music.id, name='Individual', amount=10.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=apple_music.id, name='Family', amount=16.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=apple_music.id, name='Student', amount=5.99, currency='EUR', billing_cycle='monthly')
            ]
            for plan in apple_music_plans:
                db.session.add(plan)
            services_data.append(('Apple Music', len(apple_music_plans)))

            # YouTube Premium
            youtube = Service(
                name='YouTube Premium',
                description='YouTube sans publicité avec YouTube Music',
                category_id=video_category.id if video_category else None,
                website_url='https://www.youtube.com/premium',
                logo_url='/static/uploads/logos/youtubepremium.png',
                is_active=True
            )
            db.session.add(youtube)
            db.session.flush()

            youtube_plans = [
                ServicePlan(service_id=youtube.id, name='Individual', amount=11.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=youtube.id, name='Family', amount=17.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=youtube.id, name='Student', amount=6.99, currency='EUR', billing_cycle='monthly')
            ]
            for plan in youtube_plans:
                db.session.add(plan)
            services_data.append(('YouTube Premium', len(youtube_plans)))

            # Dropbox
            dropbox = Service(
                name='Dropbox',
                description='Service de stockage cloud et partage de fichiers',
                category_id=cloud_category.id if cloud_category else None,
                website_url='https://www.dropbox.com',
                logo_url='/static/uploads/logos/dropbox.png',
                is_active=True
            )
            db.session.add(dropbox)
            db.session.flush()

            dropbox_plans = [
                ServicePlan(service_id=dropbox.id, name='Plus', amount=11.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=dropbox.id, name='Family', amount=19.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=dropbox.id, name='Professional', amount=19.99, currency='EUR', billing_cycle='monthly')
            ]
            for plan in dropbox_plans:
                db.session.add(plan)
            services_data.append(('Dropbox', len(dropbox_plans)))

            # Microsoft 365
            microsoft = Service(
                name='Microsoft 365',
                description='Suite bureautique Microsoft (Word, Excel, PowerPoint, etc.)',
                category_id=productivity_category.id if productivity_category else None,
                website_url='https://www.microsoft.com/microsoft-365',
                logo_url='/static/uploads/logos/microsoft365.png',
                is_active=True
            )
            db.session.add(microsoft)
            db.session.flush()

            microsoft_plans = [
                ServicePlan(service_id=microsoft.id, name='Personal', amount=6.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=microsoft.id, name='Family', amount=9.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=microsoft.id, name='Personal', amount=69.00, currency='EUR', billing_cycle='yearly'),
                ServicePlan(service_id=microsoft.id, name='Family', amount=99.00, currency='EUR', billing_cycle='yearly')
            ]
            for plan in microsoft_plans:
                db.session.add(plan)
            services_data.append(('Microsoft 365', len(microsoft_plans)))

            # Adobe Creative Cloud
            adobe = Service(
                name='Adobe Creative Cloud',
                description='Suite créative Adobe (Photoshop, Illustrator, etc.)',
                category_id=design_category.id if design_category else None,
                website_url='https://www.adobe.com/creativecloud.html',
                logo_url='/static/uploads/logos/adobe.png',
                is_active=True
            )
            db.session.add(adobe)
            db.session.flush()

            adobe_plans = [
                ServicePlan(service_id=adobe.id, name='Photography', amount=11.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=adobe.id, name='Single App', amount=23.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=adobe.id, name='All Apps', amount=59.99, currency='EUR', billing_cycle='monthly')
            ]
            for plan in adobe_plans:
                db.session.add(plan)
            services_data.append(('Adobe Creative Cloud', len(adobe_plans)))

            # Deezer
            deezer = Service(
                name='Deezer',
                description='Service de streaming musical français',
                category_id=audio_category.id if audio_category else None,
                website_url='https://www.deezer.com',
                logo_url='/static/uploads/logos/deezer.png',
                is_active=True
            )
            db.session.add(deezer)
            db.session.flush()

            deezer_plans = [
                ServicePlan(service_id=deezer.id, name='Free', amount=0.00, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=deezer.id, name='Premium', amount=10.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=deezer.id, name='Family', amount=17.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=deezer.id, name='Student', amount=5.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=deezer.id, name='Premium', amount=109.90, currency='EUR', billing_cycle='yearly')
            ]
            for plan in deezer_plans:
                db.session.add(plan)
            services_data.append(('Deezer', len(deezer_plans)))

            # Récupérer les catégories additionnelles
            gaming_category = Category.query.filter_by(name='Gaming').first()
            dev_category = Category.query.filter_by(name='Développement').first()

            # JetBrains
            jetbrains = Service(
                name='JetBrains',
                description='Outils de développement professionnels',
                category_id=dev_category.id if dev_category else None,
                website_url='https://www.jetbrains.com',
                logo_url='/static/uploads/logos/jetbrains.png',
                is_active=True
            )
            db.session.add(jetbrains)
            db.session.flush()

            # Helper function pour créer les plans JetBrains avec réductions de continuité
            def create_jetbrains_plan(name, monthly, yearly):
                plans = []
                # 1ère année - prix plein
                plans.append(ServicePlan(service_id=jetbrains.id, name=name, amount=monthly, currency='EUR', billing_cycle='monthly'))
                plans.append(ServicePlan(service_id=jetbrains.id, name=name, amount=yearly, currency='EUR', billing_cycle='yearly'))

                # 2ème année - 20% de réduction
                plans.append(ServicePlan(service_id=jetbrains.id, name=f'{name} - 2ème année', description='-20% de réduction', amount=round(monthly * 0.8, 2), currency='EUR', billing_cycle='monthly'))
                plans.append(ServicePlan(service_id=jetbrains.id, name=f'{name} - 2ème année', description='-20% de réduction', amount=round(yearly * 0.8, 2), currency='EUR', billing_cycle='yearly'))

                # 3ème année+ - 40% de réduction
                plans.append(ServicePlan(service_id=jetbrains.id, name=f'{name} - 3ème année+', description='-40% de réduction', amount=round(monthly * 0.6, 2), currency='EUR', billing_cycle='monthly'))
                plans.append(ServicePlan(service_id=jetbrains.id, name=f'{name} - 3ème année+', description='-40% de réduction', amount=round(yearly * 0.6, 2), currency='EUR', billing_cycle='yearly'))

                return plans

            jetbrains_plans = []

            # All Products Pack
            jetbrains_plans.extend(create_jetbrains_plan('All Products Pack', 28.90, 289.00))

            # IntelliJ IDEA Ultimate
            jetbrains_plans.extend(create_jetbrains_plan('IntelliJ IDEA Ultimate', 16.90, 169.00))

            # PyCharm Professional
            jetbrains_plans.extend(create_jetbrains_plan('PyCharm Professional', 9.90, 99.00))

            # PhpStorm
            jetbrains_plans.extend(create_jetbrains_plan('PhpStorm', 9.90, 99.00))

            # WebStorm
            jetbrains_plans.extend(create_jetbrains_plan('WebStorm', 7.90, 79.00))

            # ReSharper
            jetbrains_plans.extend(create_jetbrains_plan('ReSharper', 14.90, 149.00))

            # Rider
            jetbrains_plans.extend(create_jetbrains_plan('Rider', 14.90, 149.00))

            # CLion
            jetbrains_plans.extend(create_jetbrains_plan('CLion', 9.90, 99.00))

            # DataGrip
            jetbrains_plans.extend(create_jetbrains_plan('DataGrip', 9.90, 99.00))

            # GoLand
            jetbrains_plans.extend(create_jetbrains_plan('GoLand', 9.90, 99.00))

            # RubyMine
            jetbrains_plans.extend(create_jetbrains_plan('RubyMine', 9.90, 99.00))

            for plan in jetbrains_plans:
                db.session.add(plan)
            services_data.append(('JetBrains', len(jetbrains_plans)))

            # Subly Cloud
            subly = Service(
                name='Subly Cloud',
                description='Gestionnaire d\'abonnements intelligent',
                category_id=productivity_category.id if productivity_category else None,
                website_url='https://subly.cloud',
                is_active=True
            )
            db.session.add(subly)
            db.session.flush()

            subly_plans = [
                ServicePlan(service_id=subly.id, name='Free', amount=0.00, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=subly.id, name='Premium', amount=4.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=subly.id, name='Premium Annual', amount=49.99, currency='EUR', billing_cycle='yearly')
            ]
            for plan in subly_plans:
                db.session.add(plan)
            services_data.append(('Subly Cloud', len(subly_plans)))

            # Blizzard (Battle.net)
            blizzard = Service(
                name='Blizzard',
                description='Abonnement World of Warcraft et services Blizzard',
                category_id=gaming_category.id if gaming_category else None,
                website_url='https://www.blizzard.com',
                logo_url='/static/uploads/logos/blizzard.png',
                is_active=True
            )
            db.session.add(blizzard)
            db.session.flush()

            blizzard_plans = [
                ServicePlan(service_id=blizzard.id, name='WoW - 30 jours', amount=12.99, currency='EUR', billing_cycle='monthly'),
                ServicePlan(service_id=blizzard.id, name='WoW - 90 jours', amount=35.97, currency='EUR', billing_cycle='quarterly'),
                ServicePlan(service_id=blizzard.id, name='WoW - 180 jours', amount=65.94, currency='EUR', billing_cycle='yearly')
            ]
            for plan in blizzard_plans:
                db.session.add(plan)
            services_data.append(('Blizzard', len(blizzard_plans)))

            db.session.commit()

            total_plans = sum(count for _, count in services_data)
            print(f"{len(services_data)} services créés avec {total_plans} formules :")
            for service_name, plan_count in services_data:
                print(f"  - {service_name} ({plan_count} formule{'s' if plan_count > 1 else ''})")
        else:
            print("\nLes services existent déjà.")

        print("\n✅ Initialisation terminée avec succès !")
        print("\nVous pouvez maintenant lancer l'application avec: python run.py")


if __name__ == '__main__':
    init_database()
