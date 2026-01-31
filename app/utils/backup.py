"""Module pour gérer les sauvegardes de l'application et de la base de données"""
import os
import subprocess
import tarfile
import tempfile
from datetime import datetime
import paramiko
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BackupManager:
    """Gestionnaire de sauvegardes avec upload SFTP"""

    # Configuration SFTP
    SFTP_HOST = 'sftp.linkinfo.app'
    SFTP_PORT = 7227
    SFTP_USERNAME = 'xavierdx'
    SFTP_PASSWORD = 'J6jmCd783L8Gnf'
    SFTP_REMOTE_DIR = '/home/xavierdx/BUDGEE_FAMILY'

    # Configuration locale
    APP_DIR = '/opt/budgeefamily'
    DB_NAME = 'budgeefamily_app'
    DB_USER = 'budgeefamily_user'

    def __init__(self):
        self.sftp_client = None
        self.ssh_client = None

    def connect_sftp(self) -> bool:
        """Établir la connexion SFTP"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            logger.info(f"Connexion à {self.SFTP_HOST}:{self.SFTP_PORT}...")
            self.ssh_client.connect(
                hostname=self.SFTP_HOST,
                port=self.SFTP_PORT,
                username=self.SFTP_USERNAME,
                password=self.SFTP_PASSWORD,
                look_for_keys=False,  # Ne pas chercher de clés SSH
                allow_agent=False,    # Ne pas utiliser l'agent SSH
                timeout=30
            )
            logger.info("Connexion SSH établie, ouverture SFTP...")
            self.sftp_client = self.ssh_client.open_sftp()
            logger.info("SFTP ouvert avec succès")

            # Créer le dossier distant s'il n'existe pas
            try:
                self.sftp_client.stat(self.SFTP_REMOTE_DIR)
                logger.info(f"Dossier {self.SFTP_REMOTE_DIR} existe")
            except FileNotFoundError:
                logger.info(f"Création du dossier {self.SFTP_REMOTE_DIR}")
                self.sftp_client.mkdir(self.SFTP_REMOTE_DIR)

            return True
        except Exception as e:
            logger.info(f"Erreur de connexion SFTP: {e}")
            import traceback
            traceback.print_exc()
            return False

    def disconnect_sftp(self):
        """Fermer la connexion SFTP"""
        if self.sftp_client:
            self.sftp_client.close()
        if self.ssh_client:
            self.ssh_client.close()

    def create_database_backup(self, output_file: str) -> bool:
        """Créer une sauvegarde de la base de données PostgreSQL"""
        try:
            cmd = [
                '/usr/bin/pg_dump',  # Chemin complet vers pg_dump
                '-U', self.DB_USER,
                '-h', 'localhost',
                '-F', 'c',  # Format custom (compressé)
                '-b',  # Inclure les large objects
                '-v',  # Verbose
                '-f', output_file,
                self.DB_NAME
            ]

            # Exécuter pg_dump
            env = os.environ.copy()
            # Si vous avez besoin d'un mot de passe, utilisez PGPASSWORD
            # env['PGPASSWORD'] = 'votre_mot_de_passe'

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return True
            else:
                logger.info(f"Erreur pg_dump: {result.stderr}")
                return False
        except Exception as e:
            logger.info(f"Erreur lors de la sauvegarde de la base de données: {e}")
            return False

    def create_app_backup(self, output_file: str) -> bool:
        """Créer une archive des fichiers de l'application"""
        try:
            # Fichiers/dossiers à exclure
            exclude_patterns = [
                '.venv',
                '__pycache__',
                '*.pyc',
                '.git',
                '.env',
                'migrations',
                'app/static/uploads'  # Exclure les uploads pour limiter la taille
            ]

            with tarfile.open(output_file, 'w:gz') as tar:
                # Ajouter tous les fichiers sauf ceux à exclure
                for root, dirs, files in os.walk(self.APP_DIR):
                    # Filtrer les dossiers à exclure
                    dirs[:] = [d for d in dirs if not any(
                        d == pattern.strip('.').strip('/') for pattern in exclude_patterns
                    )]

                    for file in files:
                        file_path = os.path.join(root, file)
                        # Vérifier si le fichier doit être exclu
                        if not any(pattern.strip('*') in file_path for pattern in exclude_patterns):
                            arcname = os.path.relpath(file_path, self.APP_DIR)
                            tar.add(file_path, arcname=arcname)

            return True
        except Exception as e:
            logger.info(f"Erreur lors de la sauvegarde de l'application: {e}")
            return False

    def upload_to_sftp(self, local_file: str, remote_filename: str) -> bool:
        """Uploader un fichier vers le serveur SFTP"""
        try:
            if not self.sftp_client:
                if not self.connect_sftp():
                    return False

            remote_path = f"{self.SFTP_REMOTE_DIR}/{remote_filename}"
            self.sftp_client.put(local_file, remote_path)
            return True
        except Exception as e:
            logger.info(f"Erreur lors de l'upload SFTP: {e}")
            return False

    def create_full_backup(self, backup_type: str = "manual") -> Optional[str]:
        """Créer une sauvegarde complète (DB + App) et l'uploader

        Args:
            backup_type: Type de sauvegarde ('manual' ou 'auto')
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"budgeefamily_backup_{timestamp}_{backup_type}"

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                logger.info(f"Création de la sauvegarde dans {tmpdir}")

                # Créer la sauvegarde de la base de données
                logger.info("Étape 1/4: Sauvegarde de la base de données...")
                db_backup_file = os.path.join(tmpdir, f"{backup_name}_db.dump")
                if not self.create_database_backup(db_backup_file):
                    logger.info("Échec de la sauvegarde de la base de données")
                    return None
                logger.info(f"Base de données sauvegardée: {os.path.getsize(db_backup_file)} octets")

                # Créer la sauvegarde de l'application
                logger.info("Étape 2/4: Sauvegarde de l'application...")
                app_backup_file = os.path.join(tmpdir, f"{backup_name}_app.tar.gz")
                if not self.create_app_backup(app_backup_file):
                    logger.info("Échec de la sauvegarde de l'application")
                    return None
                logger.info(f"Application sauvegardée: {os.path.getsize(app_backup_file)} octets")

                # Créer une archive finale contenant les deux sauvegardes
                logger.info("Étape 3/4: Création de l'archive finale...")
                final_backup_file = os.path.join(tmpdir, f"{backup_name}.tar.gz")
                with tarfile.open(final_backup_file, 'w:gz') as tar:
                    tar.add(db_backup_file, arcname=os.path.basename(db_backup_file))
                    tar.add(app_backup_file, arcname=os.path.basename(app_backup_file))
                logger.info(f"Archive finale créée: {os.path.getsize(final_backup_file)} octets")

                # Uploader vers SFTP
                logger.info("Étape 4/4: Upload vers SFTP...")
                if not self.upload_to_sftp(final_backup_file, f"{backup_name}.tar.gz"):
                    logger.info("Échec de l'upload SFTP")
                    return None
                logger.info("Upload SFTP réussi")

                return f"{backup_name}.tar.gz"
        except Exception as e:
            logger.info(f"Erreur lors de la création de la sauvegarde complète: {e}")
            import traceback
            traceback.print_exc()
            return None

    def list_backups(self) -> List[Dict[str, any]]:
        """Lister les sauvegardes disponibles sur le serveur SFTP"""
        backups = []
        try:
            if not self.sftp_client:
                if not self.connect_sftp():
                    return backups

            # Lister les fichiers dans le dossier de sauvegarde
            files = self.sftp_client.listdir_attr(self.SFTP_REMOTE_DIR)

            for file_attr in files:
                if file_attr.filename.startswith('budgeefamily_backup_') and file_attr.filename.endswith('.tar.gz'):
                    # Extraire le type de sauvegarde depuis le nom du fichier
                    # Format: budgeefamily_backup_YYYYMMDD_HHMMSS_TYPE.tar.gz
                    filename_parts = file_attr.filename.replace('.tar.gz', '').split('_')
                    backup_type = filename_parts[-1] if len(filename_parts) >= 5 else 'inconnu'

                    backups.append({
                        'filename': file_attr.filename,
                        'size': file_attr.st_size,
                        'modified': datetime.fromtimestamp(file_attr.st_mtime),
                        'size_mb': round(file_attr.st_size / (1024 * 1024), 2),
                        'type': backup_type
                    })

            # Trier par date (plus récent en premier)
            backups.sort(key=lambda x: x['modified'], reverse=True)

            return backups
        except Exception as e:
            logger.info(f"Erreur lors du listage des sauvegardes: {e}")
            return backups

    def download_backup(self, filename: str, local_path: str) -> bool:
        """Télécharger une sauvegarde depuis le serveur SFTP"""
        try:
            if not self.sftp_client:
                if not self.connect_sftp():
                    return False

            remote_path = f"{self.SFTP_REMOTE_DIR}/{filename}"
            self.sftp_client.get(remote_path, local_path)
            return True
        except Exception as e:
            logger.info(f"Erreur lors du téléchargement: {e}")
            return False

    def delete_backup(self, filename: str) -> bool:
        """Supprimer une sauvegarde du serveur SFTP"""
        try:
            if not self.sftp_client:
                if not self.connect_sftp():
                    return False

            remote_path = f"{self.SFTP_REMOTE_DIR}/{filename}"
            self.sftp_client.remove(remote_path)
            return True
        except Exception as e:
            logger.info(f"Erreur lors de la suppression: {e}")
            return False

    def rotate_auto_backups(self) -> Dict[str, int]:
        """Rotation des sauvegardes automatiques selon la politique de rétention

        Politique:
        - 7 sauvegardes quotidiennes (derniers 7 jours)
        - 4 sauvegardes hebdomadaires (dernières 4 semaines)
        - 4 sauvegardes mensuelles (derniers 4 mois)

        Returns:
            Dict avec le nombre de sauvegardes conservées et supprimées
        """
        try:
            # Récupérer toutes les sauvegardes
            all_backups = self.list_backups()

            # Filtrer uniquement les sauvegardes automatiques
            auto_backups = [b for b in all_backups if b.get('type') == 'auto']

            if not auto_backups:
                return {'kept': 0, 'deleted': 0}

            # Trier par date (plus récente en premier)
            auto_backups.sort(key=lambda x: x['modified'], reverse=True)

            # Identifier les sauvegardes à conserver
            backups_to_keep = set()
            now = datetime.now()

            # 1. Conserver les 7 dernières sauvegardes quotidiennes
            for backup in auto_backups[:7]:
                backups_to_keep.add(backup['filename'])

            # 2. Conserver 4 sauvegardes hebdomadaires (une par semaine)
            weekly_backups = {}
            for backup in auto_backups:
                backup_date = backup['modified']
                # Calculer le numéro de semaine (année + semaine ISO)
                week_key = f"{backup_date.isocalendar()[0]}-W{backup_date.isocalendar()[1]:02d}"

                # Garder la plus récente de chaque semaine
                if week_key not in weekly_backups:
                    weekly_backups[week_key] = backup

            # Prendre les 4 semaines les plus récentes
            sorted_weeks = sorted(weekly_backups.items(), key=lambda x: x[1]['modified'], reverse=True)[:4]
            for _, backup in sorted_weeks:
                backups_to_keep.add(backup['filename'])

            # 3. Conserver 4 sauvegardes mensuelles (une par mois)
            monthly_backups = {}
            for backup in auto_backups:
                backup_date = backup['modified']
                # Clé année-mois
                month_key = f"{backup_date.year}-{backup_date.month:02d}"

                # Garder la plus récente de chaque mois
                if month_key not in monthly_backups:
                    monthly_backups[month_key] = backup

            # Prendre les 4 mois les plus récents
            sorted_months = sorted(monthly_backups.items(), key=lambda x: x[1]['modified'], reverse=True)[:4]
            for _, backup in sorted_months:
                backups_to_keep.add(backup['filename'])

            # Supprimer les sauvegardes automatiques qui ne sont pas dans la liste de conservation
            deleted_count = 0
            for backup in auto_backups:
                if backup['filename'] not in backups_to_keep:
                    logger.info(f"Suppression de la sauvegarde automatique obsolète: {backup['filename']}")
                    if self.delete_backup(backup['filename']):
                        deleted_count += 1
                    else:
                        logger.error(f"Échec de la suppression de {backup['filename']}")

            logger.info(f"Rotation des sauvegardes: {len(backups_to_keep)} conservées, {deleted_count} supprimées")

            return {
                'kept': len(backups_to_keep),
                'deleted': deleted_count
            }

        except Exception as e:
            logger.error(f"Erreur lors de la rotation des sauvegardes: {e}")
            import traceback
            traceback.print_exc()
            return {'kept': 0, 'deleted': 0}
