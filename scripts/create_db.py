"""Cree la base attrition, ses tables, et y insere les 3 extraits CSV.

Lancement :
    python -m scripts.create_db

Rejouable : le schema supprime et recree les tables a chaque execution.
"""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from src.features import nettoyer_pourcentage

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_DATA = RACINE / "data"
FICHIER_SCHEMA = RACINE / "sql" / "schema.sql"

# L'ordre compte : employes_sirh porte la cle referencee par les deux autres.
TABLES = {
    "employes_sirh": "extrait_sirh.csv",
    "employes_sondage": "extrait_sondage.csv",
    "employes_eval": "extrait_eval.csv",
}

load_dotenv()


def creer_base():
    """Cree la base attrition si elle n'existe pas deja."""
    # AUTOCOMMIT : PostgreSQL refuse CREATE DATABASE dans une transaction.
    moteur = create_engine(
        os.environ["DATABASE_ADMIN_URL"], isolation_level="AUTOCOMMIT"
    )
    with moteur.connect() as connexion:
        existe = connexion.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'attrition'")
        ).scalar()
        if existe:
            print("base attrition : deja presente")
        else:
            connexion.execute(text("CREATE DATABASE attrition"))
            print("base attrition : creee")


def creer_tables(moteur):
    """Rejoue sql/schema.sql."""
    with moteur.begin() as connexion:
        connexion.exec_driver_sql(FICHIER_SCHEMA.read_text(encoding="utf-8"))
    print(f"tables : {', '.join(TABLES)}, predictions")


def inserer_donnees(moteur):
    """Charge les 3 CSV dans leurs tables."""
    for table, fichier in TABLES.items():
        df = pd.read_csv(DOSSIER_DATA / fichier)
        if table == "employes_eval":
            df["id_employee"] = df["eval_number"].str.removeprefix("E_").astype(int)
            df["augementation_salaire_precedente"] = df[
                "augementation_salaire_precedente"
            ].map(nettoyer_pourcentage)
        df.to_sql(table, moteur, if_exists="append", index=False)
        print(f"{table} : {len(df)} lignes")


def main():
    creer_base()
    moteur = create_engine(os.environ["DATABASE_URL"])
    creer_tables(moteur)
    inserer_donnees(moteur)


if __name__ == "__main__":
    main()
