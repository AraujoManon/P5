"""Quelques requetes sur la base attrition.

Lancement :
    python -m scripts.requetes
"""

import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

REQUETES = {
    "Taux de depart par departement": """
        SELECT s.departement,
               count(*) AS effectif,
               round(100.0 * count(*) FILTER (
                   WHERE so.a_quitte_l_entreprise = 'Oui') / count(*), 1) AS taux_depart
        FROM employes_sirh s
        JOIN employes_sondage so ON so.code_sondage = s.id_employee
        GROUP BY s.departement
        ORDER BY taux_depart DESC
    """,
    "Taux de depart selon les heures supplementaires": """
        SELECT e.heure_supplementaires,
               count(*) AS effectif,
               round(100.0 * count(*) FILTER (
                   WHERE so.a_quitte_l_entreprise = 'Oui') / count(*), 1) AS taux_depart
        FROM employes_eval e
        JOIN employes_sondage so ON so.code_sondage = e.id_employee
        GROUP BY e.heure_supplementaires
        ORDER BY taux_depart DESC
    """,
    "Les 5 derniers appels au modele": """
        SELECT id, horodatage, probabilite, prediction, version_modele
        FROM predictions
        ORDER BY horodatage DESC
        LIMIT 5
    """,
    "Repartition des predictions": """
        SELECT prediction,
               count(*) AS nombre,
               round(avg(probabilite), 3) AS probabilite_moyenne
        FROM predictions
        GROUP BY prediction
    """,
}


def main():
    moteur = create_engine(os.environ["DATABASE_URL"])
    for titre, requete in REQUETES.items():
        print(f"\n{titre}")
        resultat = pd.read_sql(requete, moteur)
        print(resultat.to_string(index=False) if len(resultat) else "  (aucune ligne)")


if __name__ == "__main__":
    main()
