"""Contrat d'entree et de sortie de l'API.

Pydantic valide chaque requete avant qu'elle atteigne le modele, et FastAPI
se sert des memes classes pour generer la documentation Swagger. Le contrat
est ecrit une seule fois et sert a trois choses : validation, messages
d'erreur, documentation.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.features import BORNES
from src.pipeline import SEUIL_DECISION


def borne(nom: str, description: str = "") -> Any:
    """Construit un Field a partir des bornes declarees dans features.py.

    Un maximum a None donne le=None, que Pydantic interprete comme
    "pas de limite superieure".
    """
    mini, maxi = BORNES[nom]
    return Field(ge=mini, le=maxi, description=description or None)


class EmployeEntree(BaseModel):
    """Les 26 colonnes attendues pour un salarie.

    L'ordre suit COLONNES_ENTREE : 12 entiers, 7 echelles, 1 ordinale,
    6 nominales.
    """

    # extra="forbid" : un champ inconnu est refuse au lieu d'etre ignore
    # en silence. Une faute de frappe donne une erreur 422 explicite.
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "age": 41,
                "revenu_mensuel": 5993,
                "nombre_experiences_precedentes": 8,
                "annee_experience_totale": 8,
                "annees_dans_l_entreprise": 6,
                "annees_dans_le_poste_actuel": 4,
                "annees_depuis_la_derniere_promotion": 0,
                "annes_sous_responsable_actuel": 5,
                "distance_domicile_travail": 1,
                "nb_formations_suivies": 0,
                "nombre_participation_pee": 0,
                "augementation_salaire_precedente": 11,
                "satisfaction_employee_environnement": 2,
                "satisfaction_employee_nature_travail": 4,
                "satisfaction_employee_equipe": 1,
                "satisfaction_employee_equilibre_pro_perso": 1,
                "note_evaluation_precedente": 3,
                "note_evaluation_actuelle": 3,
                "niveau_education": 2,
                "frequence_deplacement": "Occasionnel",
                "genre": "F",
                "statut_marital": "Célibataire",
                "departement": "Commercial",
                "poste": "Cadre Commercial",
                "domaine_etude": "Infra & Cloud",
                "heure_supplementaires": "Oui",
            }
        },
    )

    # --- 12 entiers ---
    age: int = borne("age", "Age du salarie")
    revenu_mensuel: int = borne("revenu_mensuel", "Salaire mensuel brut en euros")
    nombre_experiences_precedentes: int = borne(
        "nombre_experiences_precedentes", "Nombre d'employeurs precedents"
    )
    annee_experience_totale: int = borne(
        "annee_experience_totale", "Annees d'experience professionnelle, tout employeur"
    )
    annees_dans_l_entreprise: int = borne(
        "annees_dans_l_entreprise", "Anciennete dans l'entreprise"
    )
    annees_dans_le_poste_actuel: int = borne(
        "annees_dans_le_poste_actuel", "Annees passees sur le poste actuel"
    )
    annees_depuis_la_derniere_promotion: int = borne(
        "annees_depuis_la_derniere_promotion", "Annees ecoulees depuis la promotion"
    )
    annes_sous_responsable_actuel: int = borne(
        "annes_sous_responsable_actuel", "Annees sous le responsable actuel"
    )
    distance_domicile_travail: int = borne(
        "distance_domicile_travail", "Distance domicile-travail en kilometres"
    )
    nb_formations_suivies: int = borne(
        "nb_formations_suivies", "Formations suivies l'an dernier"
    )
    nombre_participation_pee: int = borne(
        "nombre_participation_pee", "Participations au plan d'epargne entreprise"
    )
    augementation_salaire_precedente: int = borne(
        "augementation_salaire_precedente",
        "Derniere augmentation en pourcent, sans le signe %",
    )

    # --- 7 echelles ---
    satisfaction_employee_environnement: int = borne(
        "satisfaction_employee_environnement", "Satisfaction environnement, de 1 a 4"
    )
    satisfaction_employee_nature_travail: int = borne(
        "satisfaction_employee_nature_travail",
        "Satisfaction nature du travail, de 1 a 4",
    )
    satisfaction_employee_equipe: int = borne(
        "satisfaction_employee_equipe", "Satisfaction equipe, de 1 a 4"
    )
    satisfaction_employee_equilibre_pro_perso: int = borne(
        "satisfaction_employee_equilibre_pro_perso",
        "Satisfaction equilibre vie pro / vie perso, de 1 a 4",
    )
    note_evaluation_precedente: int = borne(
        "note_evaluation_precedente", "Note de l'evaluation precedente, de 1 a 4"
    )
    note_evaluation_actuelle: int = borne(
        "note_evaluation_actuelle", "Note de l'evaluation actuelle, de 1 a 4"
    )
    niveau_education: int = borne("niveau_education", "Niveau d'etudes, de 1 a 5")

    # --- 1 ordinale ---
    frequence_deplacement: Literal["Aucun", "Occasionnel", "Frequent"] = Field(
        description="Frequence des deplacements professionnels"
    )

    # --- 6 nominales ---
    genre: Literal["F", "M"] = Field(description="Genre du salarie")
    statut_marital: Literal["Célibataire", "Divorcé(e)", "Marié(e)"] = Field(
        description="Situation maritale"
    )
    departement: Literal["Commercial", "Consulting", "Ressources Humaines"] = Field(
        description="Departement de rattachement"
    )
    poste: Literal[
        "Assistant de Direction",
        "Cadre Commercial",
        "Consultant",
        "Directeur Technique",
        "Manager",
        "Représentant Commercial",
        "Ressources Humaines",
        "Senior Manager",
        "Tech Lead",
    ] = Field(description="Intitule du poste")
    domaine_etude: Literal[
        "Autre",
        "Entrepreunariat",
        "Infra & Cloud",
        "Marketing",
        "Ressources Humaines",
        "Transformation Digitale",
    ] = Field(description="Domaine de formation initiale")
    heure_supplementaires: Literal["Non", "Oui"] = Field(
        description="Le salarie fait-il des heures supplementaires"
    )


class PredictionSortie(BaseModel):
    """Ce que l'API renvoie pour un salarie."""

    probabilite_demission: float = Field(
        ge=0, le=1, description="Probabilite estimee de depart, entre 0 et 1"
    )
    prediction: Literal["Oui", "Non"] = Field(
        description="Depart prevu, si la probabilite depasse le seuil"
    )
    # Renvoye avec la reponse : le seuil n'est pas 0.50, sans lui une
    # probabilite de 0.45 associee a "Oui" ressemble a une erreur.
    seuil_applique: float = Field(
        default=SEUIL_DECISION, description="Seuil de decision applique"
    )
