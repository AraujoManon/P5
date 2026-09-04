"""Point d'entrée de l'API."""

from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI

from src.pipeline import SEUIL_DECISION
from src.schemas import EmployeEntree, PredictionSortie

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
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    """Verifie que le service tourne et que le modele est charge."""
    return {"statut": "ok", "modele_charge": "pipeline" in modele}


@app.post("/predict", response_model=PredictionSortie)
def predict(employe: EmployeEntree):
    """Estime le risque de depart d'un salarie."""
    donnees = pd.DataFrame([employe.model_dump()])
    probabilite = float(modele["pipeline"].predict_proba(donnees)[0, 1])
    return PredictionSortie(
        probabilite_demission=round(probabilite, 4),
        prediction="Oui" if probabilite >= SEUIL_DECISION else "Non",
    )
