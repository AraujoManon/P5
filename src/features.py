"""
Colonnes et constantes du jeu de donnees TechNova.

Toutes les autres parties du projet (entrainement, API, tests) importent
leurs constantes ici, pour eviter de les redefinir a plusieurs endroits.
"""

# Variable a predire
COLONNE_CIBLE = "a_quitte_l_entreprise"
MAPPING_CIBLE = {"Oui": 1, "Non": 0}

# Colonnes des CSV qu'on n'utilise pas, avec la raison
COLONNES_ECARTEES = {
    "id_employee": "identifiant",
    "code_sondage": "doublon de id_employee",
    "eval_number": "identifiant technique",
    "nombre_heures_travailless": "variance nulle (80 partout)",
    "nombre_employee_sous_responsabilite": "variance nulle",
    "ayant_enfants": "variance nulle",
    "niveau_hierarchique_poste": "redondant avec poste",
}

# Entiers (12)
COLONNES_ENTIERES = [
    "age",
    "revenu_mensuel",
    "nombre_experiences_precedentes",
    "annee_experience_totale",
    "annees_dans_l_entreprise",
    "annees_dans_le_poste_actuel",
    "annees_depuis_la_derniere_promotion",
    "annes_sous_responsable_actuel",
    "distance_domicile_travail",
    "nb_formations_suivies",
    "nombre_participation_pee",
    "augementation_salaire_precedente",
]

# Notes de 1 a 4 ou 1 a 5, deja numeriques et deja ordonnees (7)
COLONNES_ECHELLE = [
    "satisfaction_employee_environnement",
    "satisfaction_employee_nature_travail",
    "satisfaction_employee_equipe",
    "satisfaction_employee_equilibre_pro_perso",
    "note_evaluation_precedente",
    "note_evaluation_actuelle",
    "niveau_education",
]

# Categorielle ordonnee : Aucun < Occasionnel < Frequent (1)
COLONNE_ORDINALE = "frequence_deplacement"

# Categorielles sans ordre, a encoder en One Hot (6)
COLONNES_NOMINALES = [
    "genre",
    "statut_marital",
    "departement",
    "poste",
    "domaine_etude",
    "heure_supplementaires",
]

COLONNES_ENTREE = (
    COLONNES_ENTIERES + COLONNES_ECHELLE + [COLONNE_ORDINALE] + COLONNES_NOMINALES
)

# Bornes (min, max) de chaque champ numerique. None = pas de maximum.
# Volontairement plus larges que ce qu'on observe dans les donnees : refuser
# un salarie de 61 ans parce qu'aucun n'etait dans le jeu d'entrainement
# n'aurait aucun sens pour l'utilisateur RH.
BORNES = {
    "age": (18, 60),
    "revenu_mensuel": (1, None),
    "nombre_experiences_precedentes": (0, 20),
    "annee_experience_totale": (0, 50),
    "annees_dans_l_entreprise": (0, 50),
    "annees_dans_le_poste_actuel": (0, 50),
    "annees_depuis_la_derniere_promotion": (0, 50),
    "annes_sous_responsable_actuel": (0, 50),
    "distance_domicile_travail": (0, None),
    "nb_formations_suivies": (0, 10),
    "nombre_participation_pee": (0, 5),
    "augementation_salaire_precedente": (0, 100),  # en pourcent
    "satisfaction_employee_environnement": (1, 4),
    "satisfaction_employee_nature_travail": (1, 4),
    "satisfaction_employee_equipe": (1, 4),
    "satisfaction_employee_equilibre_pro_perso": (1, 4),
    "note_evaluation_precedente": (1, 4),
    "note_evaluation_actuelle": (1, 4),  # le jeu d'entrainement ne contient que 3 et 4
    "niveau_education": (1, 5),
}

# Valeurs autorisees pour les champs texte, relevees sur les 1470 lignes
MODALITES = {
    "genre": ["F", "M"],
    "heure_supplementaires": ["Non", "Oui"],
    "statut_marital": ["Célibataire", "Divorcé(e)", "Marié(e)"],
    "departement": ["Commercial", "Consulting", "Ressources Humaines"],
    "frequence_deplacement": ["Aucun", "Occasionnel", "Frequent"],
    "domaine_etude": [
        "Autre",
        "Entrepreunariat",
        "Infra & Cloud",
        "Marketing",
        "Ressources Humaines",
        "Transformation Digitale",
    ],
    "poste": [
        "Assistant de Direction",
        "Cadre Commercial",
        "Consultant",
        "Directeur Technique",
        "Manager",
        "Représentant Commercial",
        "Ressources Humaines",
        "Senior Manager",
        "Tech Lead",
    ],
}

# L'ordre porte de l'information, un One Hot le detruirait
ORDRE_DEPLACEMENT = {"Aucun": 0, "Occasionnel": 1, "Frequent": 2}

# Les 4 axes du sondage, moyennes en une note globale
AXES_SATISFACTION = [
    "satisfaction_employee_environnement",
    "satisfaction_employee_nature_travail",
    "satisfaction_employee_equipe",
    "satisfaction_employee_equilibre_pro_perso",
]

# Variables calculees a partir des 26 colonnes. L'API ne les recoit jamais,
# elle les recalcule elle-meme avec la meme formule qu'a l'entrainement.
FEATURES_METIER = [
    "ratio_fidelite",
    "ratio_stagnation_poste",
    "ratio_attente_promotion",
    "revenu_par_annee_experience",
    "satisfaction_moyenne",
]


def nettoyer_pourcentage(valeur):
    """Convertit "11 %" en 11.

    Le CSV stocke ce champ en texte, l'API le recoit deja en entier.
    On accepte les deux formes pour que le meme code serve des deux cotes.
    """
    if isinstance(valeur, bool):
        raise ValueError(f"Pourcentage invalide : {valeur!r}")
    if isinstance(valeur, (int, float)):
        return int(valeur)
    return int(float(str(valeur).replace("%", "").strip()))


def encoder_frequence_deplacement(valeur):
    """Traduit la frequence de deplacement en 0, 1 ou 2."""
    cle = str(valeur).strip()
    if cle not in ORDRE_DEPLACEMENT:
        raise ValueError(
            f"Frequence de deplacement inconnue : {valeur!r}. "
            f"Valeurs acceptees : {list(ORDRE_DEPLACEMENT)}"
        )
    return ORDRE_DEPLACEMENT[cle]


def creer_features_metier(df):
    """Ajoute les 5 variables metier au DataFrame.

    Les colonnes brutes sont des valeurs absolues (annees, euros). Ce qui
    declenche une demission est souvent relatif : 5 ans dans le meme poste
    n'ont pas le meme sens pour un junior et pour quelqu'un qui a 30 ans
    de carriere.

    Les denominateurs sont bornes a 1 avec clip(lower=1), sinon un salarie
    arrive depuis moins d'un an provoque une division par zero.
    """
    df = df.copy()

    # Denominateurs communs, bornes a 1
    anciennete = df["annees_dans_l_entreprise"].clip(lower=1)
    experience = df["annee_experience_totale"].clip(lower=1)

    # Part de la carriere passee dans l'entreprise
    df["ratio_fidelite"] = df["annees_dans_l_entreprise"] / experience

    # Part de l'anciennete passee sans changer de poste
    df["ratio_stagnation_poste"] = df["annees_dans_le_poste_actuel"] / anciennete

    # Attente de promotion rapportee a l'anciennete
    promotion = df["annees_depuis_la_derniere_promotion"]
    df["ratio_attente_promotion"] = promotion / anciennete

    # Ce que rapporte une annee d'experience
    df["revenu_par_annee_experience"] = df["revenu_mensuel"] / experience

    # Moyenne des 4 axes du sondage
    df["satisfaction_moyenne"] = df[AXES_SATISFACTION].mean(axis=1)

    return df


def preparer_donnees(df):
    """Nettoyage, encodage ordinal et features metier.

    Cette fonction sera branchee dans le pipeline scikit-learn, donc elle
    s'execute a l'identique a l'entrainement et dans l'API. C'est ce qui
    evite qu'une prediction soit calculee sur des donnees preparees
    differemment de celles vues a l'entrainement.
    """
    manquantes = [col for col in COLONNES_ENTREE if col not in df.columns]
    if manquantes:
        raise ValueError(f"Colonnes manquantes en entree du modele : {manquantes}")

    # Remet les colonnes dans l'ordre et jette tout ce qui n'est pas au contrat
    df = df.loc[:, COLONNES_ENTREE].copy()

    colonne_pct = "augementation_salaire_precedente"
    df[colonne_pct] = df[colonne_pct].apply(nettoyer_pourcentage)
    df[COLONNE_ORDINALE] = df[COLONNE_ORDINALE].apply(encoder_frequence_deplacement)

    return creer_features_metier(df)
