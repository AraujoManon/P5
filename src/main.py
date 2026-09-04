"""Point d'entrée de l'API."""

from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from src.database import enregistrer_prediction, get_session
from src.pipeline import SEUIL_DECISION
from src.schemas import EmployeEntree, PredictionSortie

VERSION = "0.1.0"

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


@app.post("/predict", response_model=PredictionSortie)
def predict(employe: EmployeEntree, session: Session = Depends(get_session)):
    """Estime le risque de depart d'un salarie et trace l'appel en base."""
    donnees = pd.DataFrame([employe.model_dump()])
    probabilite = float(modele["pipeline"].predict_proba(donnees)[0, 1])
    sortie = PredictionSortie(
        probabilite_demission=round(probabilite, 4),
        prediction="Oui" if probabilite >= SEUIL_DECISION else "Non",
    )
    # Pas de try/except : une prediction non tracee doit echouer, pas passer.
    enregistrer_prediction(session, employe.model_dump(), sortie, VERSION)
    return sortie
