"""Tests de l'authentification : hachage, jetons, cle de service."""

from datetime import timedelta

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src import securite
from src.database import get_session
from src.main import app
from src.schemas import EmployeEntree

EXEMPLE = EmployeEntree.model_config["json_schema_extra"]["example"]
SECRET = "secret-de-test-assez-long-pour-hs256"


class Utilisateur:
    """Tient lieu de ligne de la table utilisateurs."""

    def __init__(
        self, identifiant="martine", mot_de_passe="mot-de-passe-long", actif=True
    ):
        self.identifiant = identifiant
        self.mot_de_passe_hache = securite.hacher_mot_de_passe(mot_de_passe)
        self.actif = actif


@pytest.fixture
def compte(monkeypatch):
    """Installe un compte en base, ou aucun si on passe None."""

    def poser(utilisateur):
        monkeypatch.setattr(
            securite, "chercher_utilisateur", lambda session, identifiant: utilisateur
        )

    return poser


@pytest.fixture
def sans_base():
    """Neutralise la base : ces tests s'arretent avant l'enregistrement."""
    app.dependency_overrides[get_session] = lambda: None
    yield
    app.dependency_overrides.clear()


# --- hachage ---------------------------------------------------------------


def test_le_mot_de_passe_n_est_jamais_stocke_en_clair():
    hache = securite.hacher_mot_de_passe("mot-de-passe-long")
    assert "mot-de-passe-long" not in hache
    assert hache.startswith("$2b$")


def test_deux_hachages_du_meme_mot_de_passe_different():
    """bcrypt tire un sel par hachage : deux comptes au meme mot de passe
    ne se reconnaissent pas dans la base, et une table precalculee ne sert a rien."""
    premier = securite.hacher_mot_de_passe("mot-de-passe-long")
    second = securite.hacher_mot_de_passe("mot-de-passe-long")
    assert premier != second
    assert securite.verifier_mot_de_passe("mot-de-passe-long", premier)
    assert securite.verifier_mot_de_passe("mot-de-passe-long", second)


def test_un_mauvais_mot_de_passe_est_refuse():
    hache = securite.hacher_mot_de_passe("mot-de-passe-long")
    assert not securite.verifier_mot_de_passe("mot-de-passe-faux", hache)


# --- jetons ----------------------------------------------------------------


def test_le_jeton_porte_l_identifiant_et_se_relit(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET)
    assert securite.lire_jeton(securite.creer_jeton("martine")) == "martine"


def test_un_jeton_perime_est_refuse(monkeypatch):
    """Sans peremption, un jeton vole resterait valable indefiniment."""
    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setattr(securite, "DUREE_JETON", timedelta(seconds=-1))
    with pytest.raises(HTTPException) as erreur:
        securite.lire_jeton(securite.creer_jeton("martine"))
    assert erreur.value.status_code == 401


def test_jwt_secret_absent_du_serveur_donne_500(monkeypatch):
    """Meme raison que pour la cle d'API : c'est le serveur qui est mal configure."""
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(HTTPException) as erreur:
        securite.creer_jeton("martine")
    assert erreur.value.status_code == 500


def test_un_jeton_signe_avec_un_autre_secret_est_refuse(monkeypatch):
    """Le cas d'un jeton fabrique de toutes pieces par un attaquant."""
    monkeypatch.setenv("JWT_SECRET", SECRET)
    faux = jwt.encode(
        {"sub": "martine"},
        "autre-secret-assez-long-pour-hs256",
        algorithm=securite.ALGORITHME,
    )
    with pytest.raises(HTTPException) as erreur:
        securite.lire_jeton(faux)
    assert erreur.value.status_code == 401


# --- authentification ------------------------------------------------------


def test_un_compte_inconnu_et_un_mot_de_passe_faux_donnent_le_meme_message(compte):
    """Distinguer les deux dirait a un attaquant quels identifiants existent."""
    compte(None)
    with pytest.raises(HTTPException) as inconnu:
        securite.authentifier(None, "personne", "mot-de-passe-long")

    compte(Utilisateur())
    with pytest.raises(HTTPException) as faux:
        securite.authentifier(None, "martine", "mot-de-passe-faux")

    assert inconnu.value.status_code == faux.value.status_code == 401
    assert inconnu.value.detail == faux.value.detail


def test_un_compte_desactive_est_refuse(compte):
    compte(Utilisateur(actif=False))
    with pytest.raises(HTTPException) as erreur:
        securite.authentifier(None, "martine", "mot-de-passe-long")
    assert erreur.value.status_code == 401


# --- les deux voies d'entree de /predict -----------------------------------


def test_predict_accepte_un_jeton_d_utilisateur(session, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET)
    jeton = securite.creer_jeton("martine")
    with TestClient(app) as client:
        reponse = client.post(
            "/predict", json=EXEMPLE, headers={"Authorization": f"Bearer {jeton}"}
        )
    assert reponse.status_code == 200
    assert session.ecritures[0]["appelant"] == "martine"


def test_predict_accepte_la_cle_de_service(session, entetes):
    with TestClient(app) as client:
        reponse = client.post("/predict", json=EXEMPLE, headers=entetes)
    assert reponse.status_code == 200
    assert session.ecritures[0]["appelant"] == "service"


def test_predict_refuse_sans_rien(session):
    with TestClient(app) as client:
        reponse = client.post("/predict", json=EXEMPLE)
    assert reponse.status_code == 401
    assert session.ecritures == []


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


# --- la route /token -------------------------------------------------------


def test_token_rend_un_jeton_utilisable(session, compte, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET)
    compte(Utilisateur())
    with TestClient(app) as client:
        reponse = client.post(
            "/token", data={"username": "martine", "password": "mot-de-passe-long"}
        )
    assert reponse.status_code == 200
    assert securite.lire_jeton(reponse.json()["access_token"]) == "martine"


def test_token_refuse_un_mauvais_mot_de_passe(session, compte, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET)
    compte(Utilisateur())
    with TestClient(app) as client:
        reponse = client.post(
            "/token", data={"username": "martine", "password": "mot-de-passe-faux"}
        )
    assert reponse.status_code == 401
