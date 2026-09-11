"""Tests de l'authentification, y compris le cas ou le serveur est mal configure."""

import pytest
from fastapi.testclient import TestClient

from src.database import get_session
from src.main import app
from src.schemas import EmployeEntree

EXEMPLE = EmployeEntree.model_config["json_schema_extra"]["example"]


@pytest.fixture
def sans_base():
    """Neutralise la base : ces tests s'arretent avant l'enregistrement."""
    app.dependency_overrides[get_session] = lambda: None
    yield
    app.dependency_overrides.clear()


def test_api_key_absente_du_serveur_donne_500(sans_base, monkeypatch):
    """500 et pas 401 : c'est le serveur qui est mal configure, pas le client.

    Un 401 dirait a l'appelant que sa cle est mauvaise, et il chercherait
    au mauvais endroit.
    """
    monkeypatch.delenv("API_KEY", raising=False)
    with TestClient(app) as client:
        reponse = client.post(
            "/predict", json=EXEMPLE, headers={"X-API-Key": "peu importe"}
        )
    assert reponse.status_code == 500
