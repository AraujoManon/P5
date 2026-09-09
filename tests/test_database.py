"""Tests de la connexion : ouverture paresseuse et fermeture systematique."""

import pytest

from src import database


class SessionFactice:
    """Retient si elle a ete fermee."""

    def __init__(self):
        self.fermee = False

    def close(self):
        self.fermee = True


def test_la_fabrique_est_construite_une_seule_fois(monkeypatch):
    """Le moteur est ouvert a la premiere requete, puis reutilise."""
    monkeypatch.setattr(database, "_fabrique", {})
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    assert database.fabrique_session() is database.fabrique_session()


def test_la_session_est_fermee_meme_si_la_route_echoue(monkeypatch):
    """Sans le finally, une route en erreur laisserait la connexion ouverte."""
    factice = SessionFactice()
    monkeypatch.setattr(database, "fabrique_session", lambda: lambda: factice)

    generateur = database.get_session()
    next(generateur)
    with pytest.raises(RuntimeError):
        generateur.throw(RuntimeError("route en echec"))

    assert factice.fermee
