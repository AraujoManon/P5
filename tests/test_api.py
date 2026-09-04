"""Tests des routes de l'API.

Les tests passent par TestClient, qui appelle l'application en memoire :
pas de serveur a lancer, pas de port a ouvrir, donc ils tournent aussi
bien en local que dans la CI.
"""

from fastapi.testclient import TestClient

from src.main import app
from src.pipeline import SEUIL_DECISION
from src.schemas import EmployeEntree

# Relu depuis le schema plutot que recopie ici : si l'exemple de Swagger
# change, les tests suivent au lieu de tester un employe qui n'existe plus.
EXEMPLE = EmployeEntree.model_config["json_schema_extra"]["example"]


def test_health_repond_et_le_modele_est_charge():
    with TestClient(app) as client:
        reponse = client.get("/health")
    assert reponse.status_code == 200
    assert reponse.json()["modele_charge"] is True


def test_predict_renvoie_une_prediction_coherente():
    with TestClient(app) as client:
        reponse = client.post("/predict", json=EXEMPLE)
    assert reponse.status_code == 200
    corps = reponse.json()
    # Pas de valeur en dur : la probabilite bouge a chaque reentrainement.
    # On verifie ce qui reste vrai quel que soit le modele.
    assert 0 <= corps["probabilite_demission"] <= 1
    attendu = "Oui" if corps["probabilite_demission"] >= SEUIL_DECISION else "Non"
    assert corps["prediction"] == attendu


def test_predict_refuse_un_champ_inconnu():
    """Verifie que Pydantic est bien branche sur la route.

    Pendant de extra="forbid" cote schema : une faute de frappe doit
    donner une 422 explicite, pas une prediction calculee sur un champ
    manquant.
    """
    with TestClient(app) as client:
        reponse = client.post("/predict", json={**EXEMPLE, "agee": 41})
    assert reponse.status_code == 422
