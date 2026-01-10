"""
Mapping entre les codes pays (ISO 3166-1 alpha-2) et les fuseaux horaires
"""

# Mapping pays -> fuseau horaire principal
COUNTRY_TIMEZONES = {
    # Europe
    'FR': 'Europe/Paris',       # France
    'ES': 'Europe/Madrid',       # Espagne
    'IT': 'Europe/Rome',         # Italie
    'DE': 'Europe/Berlin',       # Allemagne
    'GB': 'Europe/London',       # Royaume-Uni
    'PT': 'Europe/Lisbon',       # Portugal
    'BE': 'Europe/Brussels',     # Belgique
    'NL': 'Europe/Amsterdam',    # Pays-Bas
    'CH': 'Europe/Zurich',       # Suisse
    'AT': 'Europe/Vienna',       # Autriche
    'SE': 'Europe/Stockholm',    # Suède
    'NO': 'Europe/Oslo',         # Norvège
    'DK': 'Europe/Copenhagen',   # Danemark
    'FI': 'Europe/Helsinki',     # Finlande
    'PL': 'Europe/Warsaw',       # Pologne
    'CZ': 'Europe/Prague',       # République tchèque
    'GR': 'Europe/Athens',       # Grèce
    'IE': 'Europe/Dublin',       # Irlande
    'RO': 'Europe/Bucharest',    # Roumanie
    'HU': 'Europe/Budapest',     # Hongrie
    'BG': 'Europe/Sofia',        # Bulgarie
    'HR': 'Europe/Zagreb',       # Croatie
    'SK': 'Europe/Bratislava',   # Slovaquie
    'SI': 'Europe/Ljubljana',    # Slovénie
    'RS': 'Europe/Belgrade',     # Serbie
    'UA': 'Europe/Kiev',         # Ukraine
    'RU': 'Europe/Moscow',       # Russie

    # Amérique du Nord
    'US': 'America/New_York',    # États-Unis (Est par défaut)
    'CA': 'America/Toronto',     # Canada (Est par défaut)
    'MX': 'America/Mexico_City', # Mexique

    # Amérique du Sud
    'BR': 'America/Sao_Paulo',   # Brésil
    'AR': 'America/Argentina/Buenos_Aires',  # Argentine
    'CL': 'America/Santiago',    # Chili
    'CO': 'America/Bogota',      # Colombie
    'PE': 'America/Lima',        # Pérou
    'VE': 'America/Caracas',     # Venezuela

    # Asie
    'CN': 'Asia/Shanghai',       # Chine
    'JP': 'Asia/Tokyo',          # Japon
    'IN': 'Asia/Kolkata',        # Inde
    'KR': 'Asia/Seoul',          # Corée du Sud
    'SG': 'Asia/Singapore',      # Singapour
    'TH': 'Asia/Bangkok',        # Thaïlande
    'VN': 'Asia/Ho_Chi_Minh',    # Vietnam
    'MY': 'Asia/Kuala_Lumpur',   # Malaisie
    'ID': 'Asia/Jakarta',        # Indonésie
    'PH': 'Asia/Manila',         # Philippines
    'TW': 'Asia/Taipei',         # Taïwan
    'HK': 'Asia/Hong_Kong',      # Hong Kong
    'AE': 'Asia/Dubai',          # Émirats arabes unis
    'SA': 'Asia/Riyadh',         # Arabie saoudite
    'IL': 'Asia/Jerusalem',      # Israël
    'TR': 'Europe/Istanbul',     # Turquie

    # Océanie
    'AU': 'Australia/Sydney',    # Australie (Est par défaut)
    'NZ': 'Pacific/Auckland',    # Nouvelle-Zélande

    # Afrique
    'ZA': 'Africa/Johannesburg', # Afrique du Sud
    'EG': 'Africa/Cairo',        # Égypte
    'MA': 'Africa/Casablanca',   # Maroc
    'TN': 'Africa/Tunis',        # Tunisie
    'DZ': 'Africa/Algiers',      # Algérie
    'KE': 'Africa/Nairobi',      # Kenya
    'NG': 'Africa/Lagos',        # Nigeria
    'SN': 'Africa/Dakar',        # Sénégal
    'CI': 'Africa/Abidjan',      # Côte d'Ivoire

    # DOM-TOM français
    'GP': 'America/Guadeloupe',  # Guadeloupe
    'MQ': 'America/Martinique',  # Martinique
    'GF': 'America/Cayenne',     # Guyane
    'RE': 'Indian/Reunion',      # Réunion
    'YT': 'Indian/Mayotte',      # Mayotte
    'NC': 'Pacific/Noumea',      # Nouvelle-Calédonie
    'PF': 'Pacific/Tahiti',      # Polynésie française
}

# Liste des pays avec leur nom complet pour le formulaire
COUNTRIES = [
    ('FR', 'France'),
    ('ES', 'Espagne'),
    ('IT', 'Italie'),
    ('DE', 'Allemagne'),
    ('GB', 'Royaume-Uni'),
    ('PT', 'Portugal'),
    ('BE', 'Belgique'),
    ('NL', 'Pays-Bas'),
    ('CH', 'Suisse'),
    ('AT', 'Autriche'),
    ('SE', 'Suède'),
    ('NO', 'Norvège'),
    ('DK', 'Danemark'),
    ('FI', 'Finlande'),
    ('PL', 'Pologne'),
    ('CZ', 'République tchèque'),
    ('GR', 'Grèce'),
    ('IE', 'Irlande'),
    ('RO', 'Roumanie'),
    ('HU', 'Hongrie'),
    ('BG', 'Bulgarie'),
    ('HR', 'Croatie'),
    ('SK', 'Slovaquie'),
    ('SI', 'Slovénie'),
    ('RS', 'Serbie'),
    ('UA', 'Ukraine'),
    ('RU', 'Russie'),
    ('US', 'États-Unis'),
    ('CA', 'Canada'),
    ('MX', 'Mexique'),
    ('BR', 'Brésil'),
    ('AR', 'Argentine'),
    ('CL', 'Chili'),
    ('CO', 'Colombie'),
    ('PE', 'Pérou'),
    ('VE', 'Venezuela'),
    ('CN', 'Chine'),
    ('JP', 'Japon'),
    ('IN', 'Inde'),
    ('KR', 'Corée du Sud'),
    ('SG', 'Singapour'),
    ('TH', 'Thaïlande'),
    ('VN', 'Vietnam'),
    ('MY', 'Malaisie'),
    ('ID', 'Indonésie'),
    ('PH', 'Philippines'),
    ('TW', 'Taïwan'),
    ('HK', 'Hong Kong'),
    ('AE', 'Émirats arabes unis'),
    ('SA', 'Arabie saoudite'),
    ('IL', 'Israël'),
    ('TR', 'Turquie'),
    ('AU', 'Australie'),
    ('NZ', 'Nouvelle-Zélande'),
    ('ZA', 'Afrique du Sud'),
    ('EG', 'Égypte'),
    ('MA', 'Maroc'),
    ('TN', 'Tunisie'),
    ('DZ', 'Algérie'),
    ('KE', 'Kenya'),
    ('NG', 'Nigeria'),
    ('SN', 'Sénégal'),
    ('CI', 'Côte d\'Ivoire'),
    ('GP', 'Guadeloupe'),
    ('MQ', 'Martinique'),
    ('GF', 'Guyane'),
    ('RE', 'Réunion'),
    ('YT', 'Mayotte'),
    ('NC', 'Nouvelle-Calédonie'),
    ('PF', 'Polynésie française'),
]


def get_timezone_for_country(country_code):
    """
    Retourne le fuseau horaire pour un code pays donné

    Args:
        country_code: Code pays ISO 3166-1 alpha-2 (ex: 'FR', 'US')

    Returns:
        str: Nom du fuseau horaire (ex: 'Europe/Paris')
    """
    return COUNTRY_TIMEZONES.get(country_code, 'Europe/Paris')


def get_country_name(country_code):
    """
    Retourne le nom complet d'un pays depuis son code

    Args:
        country_code: Code pays ISO 3166-1 alpha-2 (ex: 'FR', 'US')

    Returns:
        str: Nom complet du pays ou None si non trouvé
    """
    for code, name in COUNTRIES:
        if code == country_code:
            return name
    return None
