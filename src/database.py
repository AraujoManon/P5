"""Connexion PostgreSQL et enregistrement des predictions."""

import json
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

INSERTION = text(
    "INSERT INTO predictions "
    "(entree, probabilite, prediction, seuil_applique, version_modele) "
    "VALUES (cast(:entree as jsonb), :probabilite, :prediction, :seuil, :version)"
)

# Ouvert a la premiere requete, pas a l'import : les tests tournent sans PostgreSQL.
_fabrique = {}


def fabrique_session():
    """Le sessionmaker, construit une fois puis reutilise."""
    if "sessionmaker" not in _fabrique:
        moteur = create_engine(os.environ["DATABASE_URL"])
        _fabrique["sessionmaker"] = sessionmaker(bind=moteur)
    return _fabrique["sessionmaker"]


def get_session():
    """Une session par requete, fermee a la fin meme si la route echoue."""
    session = fabrique_session()()
    try:
        yield session
    finally:
        session.close()


def enregistrer_prediction(session, entree, sortie, version_modele):
    """Trace un appel au modele : ce qui est entre, ce qui est sorti."""
    session.execute(
        INSERTION,
        {
            "entree": json.dumps(entree, ensure_ascii=False),
            "probabilite": sortie.probabilite_demission,
            "prediction": sortie.prediction,
            "seuil": sortie.seuil_applique,
            "version": version_modele,
        },
    )
    session.commit()
