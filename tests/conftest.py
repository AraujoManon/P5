"""Fixtures partagees par les tests qui passent par l'API."""

import pytest

from src.database import get_session
from src.main import app

CLE = "cle-de-test"


class SessionFactice:
    """Tient lieu de session PostgreSQL et retient ce qu'on lui demande d'ecrire."""

    def __init__(self):
        self.ecritures = []

    def execute(self, requete, parametres):
        self.ecritures.append(parametres)

    def commit(self):
        pass


@pytest.fixture
def entetes(monkeypatch):
    """La cle de service, cote serveur comme cote client."""
    monkeypatch.setenv("API_KEY", CLE)
    return {"X-API-Key": CLE}


@pytest.fixture
def session():
    """Remplace la session PostgreSQL le temps du test."""
    factice = SessionFactice()
    app.dependency_overrides[get_session] = lambda: factice
    yield factice
    app.dependency_overrides.clear()
