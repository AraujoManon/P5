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


class SessionQuiRepond:
    """Retient la requete recue et rend la ligne qu'on lui a confiee."""

    def __init__(self, ligne):
        self.ligne = ligne
        self.parametres = None

    def execute(self, requete, parametres):
        self.parametres = parametres
        return self

    def first(self):
        return self.ligne


def test_chercher_utilisateur_interroge_la_base_sur_l_identifiant():
    session = SessionQuiRepond(ligne="la ligne du compte")
    assert database.chercher_utilisateur(session, "martine") == "la ligne du compte"
    assert session.parametres == {"identifiant": "martine"}
