"""Fait tourner le modele sur tous les employes de la base.

Lancement :
    python -m scripts.scorer_base

Lit les 3 tables, predit, et ecrit une ligne par employe dans predictions.
"""

import json
from pathlib import Path

import joblib
import pandas as pd

from src.database import INSERTION, fabrique_session
from src.features import COLONNES_ENTREE
from src.pipeline import SEUIL_DECISION

RACINE = Path(__file__).resolve().parent.parent
FICHIER_MODELE = RACINE / "models" / "attrition_model.joblib"
VERSION = "0.1.0"

REQUETE_EMPLOYES = """
    SELECT s.*, so.*, e.*
    FROM employes_sirh s
    JOIN employes_sondage so ON so.code_sondage = s.id_employee
    JOIN employes_eval e ON e.id_employee = s.id_employee
    ORDER BY s.id_employee
"""


def main():
    fabrique = fabrique_session()
    with fabrique() as session:
        df = pd.read_sql(REQUETE_EMPLOYES, session.connection())
        entrees = df[COLONNES_ENTREE]
        probabilites = joblib.load(FICHIER_MODELE).predict_proba(entrees)[:, 1]

        lignes = [
            {
                "entree": json.dumps(entree, ensure_ascii=False),
                "probabilite": round(float(p), 4),
                "prediction": "Oui" if p >= SEUIL_DECISION else "Non",
                "seuil": SEUIL_DECISION,
                "version": VERSION,
            }
            for entree, p in zip(entrees.to_dict("records"), probabilites)
        ]
        session.execute(INSERTION, lignes)
        session.commit()

    a_risque = sum(1 for ligne in lignes if ligne["prediction"] == "Oui")
    print(f"{len(lignes)} employes scores, {a_risque} signales a risque")


if __name__ == "__main__":
    main()
