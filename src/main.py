"""Point d'entrée de l'API."""

import os
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path

import joblib
import pandas as pd
import uvicorn
from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.database import enregistrer_prediction, get_session
from src.pipeline import SEUIL_DECISION
from src.securite import authentifier, creer_jeton, identifier_appelant
from src.schemas import EmployeEntree, Jeton, PredictionSortie

# Lue depuis pyproject.toml : cette valeur part dans chaque ligne de
# predictions, elle ne doit pas pouvoir diverger de la version publiee.
VERSION = version("attrition-api")

FICHIER_MODELE = (
    Path(__file__).resolve().parent.parent / "models" / "attrition_model.joblib"
)

modele = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Charge le modèle au démarrage, le libère à l'arrêt."""
    modele["pipeline"] = joblib.load(FICHIER_MODELE)
    yield
    modele.clear()


app = FastAPI(
    title="API de prédiction du risque de démission",
    description="Expose le modèle d'attrition de TechNova Partners.",
    version=VERSION,
    lifespan=lifespan,
)


@app.get("/health")
def health():
    """Verifie que le service tourne et que le modele est charge."""
    return {"statut": "ok", "modele_charge": "pipeline" in modele}


@app.post("/token", response_model=Jeton)
def token(
    formulaire: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    """Echange un identifiant et un mot de passe contre un jeton d'acces."""
    identifiant = authentifier(session, formulaire.username, formulaire.password)
    return Jeton(access_token=creer_jeton(identifiant))


@app.post("/predict", response_model=PredictionSortie)
def predict(
    employe: EmployeEntree,
    appelant: str = Depends(identifier_appelant),
    session: Session = Depends(get_session),
):
    """Estime le risque de depart d'un salarie et trace l'appel en base."""
    donnees = pd.DataFrame([employe.model_dump()])
    probabilite = float(modele["pipeline"].predict_proba(donnees)[0, 1])
    sortie = PredictionSortie(
        probabilite_demission=round(probabilite, 4),
        prediction="Oui" if probabilite >= SEUIL_DECISION else "Non",
    )
    # Pas de try/except : une prediction non tracee doit echouer, pas passer.
    enregistrer_prediction(session, employe.model_dump(), sortie, VERSION, appelant)
    return sortie


def demarrer():
    """Point d'entree `attrition-api`. PORT est impose par l'hebergeur."""
    uvicorn.run("src.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
