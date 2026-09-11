"""Tests des routes de l'API, via TestClient (pas de serveur a lancer)."""

import pytest
from fastapi.testclient import TestClient

from src.main import app, demarrer
from src.pipeline import SEUIL_DECISION
from src.schemas import EmployeEntree
from tests.conftest import CLE

# Relu depuis le schema : si l'exemple change, les tests suivent.
EXEMPLE = EmployeEntree.model_config["json_schema_extra"]["example"]


def test_health_ne_demande_pas_de_cle():
    """La supervision doit pouvoir interroger le service sans secret."""
    with TestClient(app) as client:
        reponse = client.get("/health")
    assert reponse.status_code == 200
    assert reponse.json()["modele_charge"] is True


@pytest.mark.parametrize(
    "entetes_envoyes",
    [{}, {"X-API-Key": "mauvaise-cle"}],
    ids=["sans cle", "cle fausse"],
)
def test_predict_refuse_sans_bonne_cle(session, monkeypatch, entetes_envoyes):
    monkeypatch.setenv("API_KEY", CLE)
    with TestClient(app) as client:
        reponse = client.post("/predict", json=EXEMPLE, headers=entetes_envoyes)
    assert reponse.status_code == 401
    assert session.ecritures == []


def test_predict_renvoie_une_prediction_coherente(session, entetes):
    with TestClient(app) as client:
        reponse = client.post("/predict", json=EXEMPLE, headers=entetes)
    assert reponse.status_code == 200
    corps = reponse.json()
    # Pas de valeur en dur : la probabilite bouge a chaque reentrainement.
    assert 0 <= corps["probabilite_demission"] <= 1
    attendu = "Oui" if corps["probabilite_demission"] >= SEUIL_DECISION else "Non"
    assert corps["prediction"] == attendu


def test_predict_enregistre_l_appel(session, entetes):
    with TestClient(app) as client:
        reponse = client.post("/predict", json=EXEMPLE, headers=entetes)
    assert len(session.ecritures) == 1
    ligne = session.ecritures[0]
    assert ligne["prediction"] == reponse.json()["prediction"]
    assert ligne["version"] == app.version
    assert '"age": 41' in ligne["entree"]


def test_predict_refuse_un_champ_inconnu(session, entetes):
    """Pendant de extra="forbid" : une faute de frappe donne une 422."""
    with TestClient(app) as client:
        reponse = client.post("/predict", json={**EXEMPLE, "agee": 41}, headers=entetes)
    assert reponse.status_code == 422
    assert session.ecritures == []


def test_demarrer_ecoute_le_port_de_l_hebergeur(monkeypatch):
    """L'hebergeur impose son port par PORT : le coder en dur casse le deploiement."""
    appel = {}
    monkeypatch.setenv("PORT", "7860")
    monkeypatch.setattr("src.main.uvicorn.run", lambda *a, **kw: appel.update(kw))
    demarrer()
    assert appel["port"] == 7860
