"""Tests des garde-fous de preparation : ce qui doit passer, ce qui doit lever."""

import pandas as pd
import pytest

from src.features import (
    COLONNES_ENTREE,
    FEATURES_METIER,
    ORDRE_DEPLACEMENT,
    creer_features_metier,
    encoder_frequence_deplacement,
    nettoyer_pourcentage,
    preparer_donnees,
)
from src.schemas import EmployeEntree

EXEMPLE = EmployeEntree.model_config["json_schema_extra"]["example"]


@pytest.mark.parametrize(
    "valeur",
    ["11 %", "11%", " 11 % ", 11, 11.0],
    ids=["csv", "sans espace", "avec espaces", "entier", "flottant"],
)
def test_nettoyer_pourcentage_accepte_les_deux_formes(valeur):
    """Le CSV envoie du texte, l'API un nombre : les deux donnent 11."""
    assert nettoyer_pourcentage(valeur) == 11


def test_nettoyer_pourcentage_refuse_un_booleen():
    """isinstance(True, int) est vrai : sans la garde, True passerait pour 1 %."""
    with pytest.raises(ValueError):
        nettoyer_pourcentage(True)


def test_encoder_frequence_deplacement_respecte_l_ordre():
    """L'ordre est croissant : c'est toute la raison de ne pas faire de One Hot."""
    assert encoder_frequence_deplacement("Aucun") == 0
    assert encoder_frequence_deplacement("Occasionnel") == 1
    assert encoder_frequence_deplacement("Frequent") == 2


def test_encoder_frequence_deplacement_refuse_une_modalite_inconnue():
    with pytest.raises(ValueError):
        encoder_frequence_deplacement("Tous les jours")


def test_preparer_donnees_refuse_une_colonne_manquante():
    """Mieux vaut lever que prédire sur une colonne absente remplie de NaN."""
    df = pd.DataFrame([EXEMPLE]).drop(columns=["age"])
    with pytest.raises(ValueError):
        preparer_donnees(df)


def test_preparer_donnees_sort_les_colonnes_du_contrat_plus_les_features():
    """Colonnes en trop jetées, ordre fixé, 5 variables métier ajoutées."""
    df = pd.DataFrame([{**EXEMPLE, "id_employee": 1}])
    prepare = preparer_donnees(df)
    assert list(prepare.columns) == COLONNES_ENTREE + FEATURES_METIER


def test_preparer_donnees_encode_les_colonnes_ordinales():
    df = pd.DataFrame([EXEMPLE])
    prepare = preparer_donnees(df)
    attendu = ORDRE_DEPLACEMENT[EXEMPLE["frequence_deplacement"]]
    assert prepare["frequence_deplacement"].iloc[0] == attendu


def test_creer_features_metier_ne_divise_pas_par_zero():
    """Un salarié arrivé il y a moins d'un an : les dénominateurs sont bornés à 1."""
    df = pd.DataFrame([{**EXEMPLE, "annees_dans_l_entreprise": 0}])
    calcule = creer_features_metier(preparer_donnees(df)[COLONNES_ENTREE])
    assert calcule[FEATURES_METIER].notna().all(axis=None)
