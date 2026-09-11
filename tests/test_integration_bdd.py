"""Tests du SGBD contre un vrai PostgreSQL : insertion, suppression, contraintes.

Sautes si DATABASE_TEST_URL est absente. Ne jamais y mettre la base de travail :
le schema commence par des DROP.
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

load_dotenv()

URL = os.environ.get("DATABASE_TEST_URL")

pytestmark = pytest.mark.skipif(
    not URL, reason="DATABASE_TEST_URL absente : tests d'integration sautes"
)

SCHEMA = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"

PREDICTION = {
    "entree": '{"poste": "Consultant", "age": 41}',
    "probabilite": 0.83,
    "prediction": "Oui",
    "seuil": 0.40,
    "version": "0.7.0",
}

INSERTION_PREDICTION = text(
    "INSERT INTO predictions "
    "(entree, probabilite, prediction, seuil_applique, version_modele) "
    "VALUES (cast(:entree as jsonb), :probabilite, :prediction, :seuil, :version) "
    "RETURNING id, horodatage, appelant"
)

EMPLOYE = {
    "id_employee": 1,
    "age": 41,
    "genre": "F",
    "revenu_mensuel": 5993,
    "statut_marital": "Célibataire",
    "departement": "Commercial",
    "poste": "Cadre Commercial",
    "nombre_experiences_precedentes": 8,
    "nombre_heures_travailless": 80,
    "annee_experience_totale": 8,
    "annees_dans_l_entreprise": 6,
    "annees_dans_le_poste_actuel": 4,
}

SONDAGE = {
    "code_sondage": 1,
    "a_quitte_l_entreprise": "Oui",
    "nombre_participation_pee": 0,
    "nb_formations_suivies": 0,
    "nombre_employee_sous_responsabilite": 1,
    "distance_domicile_travail": 1,
    "niveau_education": 2,
    "domaine_etude": "Infra & Cloud",
    "ayant_enfants": "Y",
    "frequence_deplacement": "Occasionnel",
    "annees_depuis_la_derniere_promotion": 0,
    "annes_sous_responsable_actuel": 5,
}


def inserer(connexion, table, valeurs):
    colonnes = ", ".join(valeurs)
    parametres = ", ".join(f":{nom}" for nom in valeurs)
    connexion.execute(
        text(f"INSERT INTO {table} ({colonnes}) VALUES ({parametres})"), valeurs
    )


@pytest.fixture(scope="module")
def moteur():
    """Rejoue le schema une fois, sur la base de test."""
    moteur = create_engine(URL)
    with moteur.begin() as connexion:
        connexion.execute(text(SCHEMA.read_text(encoding="utf-8")))
    yield moteur
    moteur.dispose()


@pytest.fixture
def connexion(moteur):
    """Une transaction par test, annulee a la fin : aucun test n'en pollue un autre."""
    with moteur.connect() as connexion:
        transaction = connexion.begin()
        yield connexion
        transaction.rollback()


# --- le schema est bien en place -------------------------------------------


def test_les_cinq_tables_existent(connexion):
    tables = {
        ligne[0]
        for ligne in connexion.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
    }
    assert {
        "employes_sirh",
        "employes_sondage",
        "employes_eval",
        "predictions",
        "utilisateurs",
    } <= tables


# --- insertion et suppression ----------------------------------------------


def test_une_prediction_s_insere_et_se_relit(connexion):
    ligne = connexion.execute(INSERTION_PREDICTION, PREDICTION).first()
    assert ligne.id > 0
    # Valeurs posees par la base, pas par le code : defaut et horodatage.
    assert ligne.appelant == "inconnu"
    assert ligne.horodatage is not None

    relue = connexion.execute(
        text("SELECT probabilite, prediction FROM predictions WHERE id = :id"),
        {"id": ligne.id},
    ).first()
    assert float(relue.probabilite) == 0.83
    assert relue.prediction == "Oui"


def test_le_jsonb_reste_interrogeable(connexion):
    """L'entree est stockee en bloc, mais chaque champ reste requetable."""
    connexion.execute(INSERTION_PREDICTION, PREDICTION)
    poste = connexion.execute(
        text("SELECT entree->>'poste' FROM predictions ORDER BY id DESC LIMIT 1")
    ).scalar()
    assert poste == "Consultant"


def test_une_prediction_se_supprime(connexion):
    identifiant = connexion.execute(INSERTION_PREDICTION, PREDICTION).first().id
    connexion.execute(
        text("DELETE FROM predictions WHERE id = :id"), {"id": identifiant}
    )
    reste = connexion.execute(
        text("SELECT count(*) FROM predictions WHERE id = :id"), {"id": identifiant}
    ).scalar()
    assert reste == 0


def test_un_employe_reference_ne_se_supprime_pas(connexion):
    """La cle etrangere interdit de laisser un sondage orphelin."""
    inserer(connexion, "employes_sirh", EMPLOYE)
    inserer(connexion, "employes_sondage", SONDAGE)
    with pytest.raises(IntegrityError):
        connexion.execute(text("DELETE FROM employes_sirh WHERE id_employee = 1"))


# --- integrite des donnees -------------------------------------------------


def test_une_probabilite_hors_bornes_est_refusee(connexion):
    """Le CHECK attrape une sortie de modele aberrante des l'ecriture."""
    with pytest.raises(IntegrityError):
        connexion.execute(INSERTION_PREDICTION, {**PREDICTION, "probabilite": 1.5})


def test_une_decision_hors_vocabulaire_est_refusee(connexion):
    with pytest.raises(IntegrityError):
        connexion.execute(
            INSERTION_PREDICTION, {**PREDICTION, "prediction": "Peut-etre"}
        )


def test_une_colonne_obligatoire_absente_est_refusee(connexion):
    with pytest.raises(IntegrityError):
        connexion.execute(
            text(
                "INSERT INTO predictions (probabilite, prediction, seuil_applique, "
                "version_modele) VALUES (0.5, 'Non', 0.4, '0.7.0')"
            )
        )


def test_un_sondage_sans_employe_est_refuse(connexion):
    with pytest.raises(IntegrityError):
        inserer(connexion, "employes_sondage", {**SONDAGE, "code_sondage": 999999})


def test_un_age_en_toutes_lettres_est_refuse(connexion):
    """Le typage des colonnes refuse ce qu'un CSV mal formé apporterait."""
    with pytest.raises(DBAPIError):
        inserer(connexion, "employes_sirh", {**EMPLOYE, "age": "quarante-et-un"})


# --- comptes d'acces -------------------------------------------------------


def test_deux_comptes_ne_peuvent_pas_porter_le_meme_identifiant(connexion):
    compte = {"identifiant": "martine", "mot_de_passe_hache": "$2b$12$peu-importe"}
    inserer(connexion, "utilisateurs", compte)
    with pytest.raises(IntegrityError):
        inserer(connexion, "utilisateurs", compte)


def test_un_compte_est_actif_par_defaut(connexion):
    inserer(
        connexion,
        "utilisateurs",
        {"identifiant": "martine", "mot_de_passe_hache": "$2b$12$peu-importe"},
    )
    actif = connexion.execute(
        text("SELECT actif FROM utilisateurs WHERE identifiant = 'martine'")
    ).scalar()
    assert actif is True
