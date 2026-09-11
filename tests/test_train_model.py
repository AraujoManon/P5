"""Tests des garde-fous du chargement des donnees d'entrainement."""

import pandas as pd
import pytest

from scripts import train_model


@pytest.fixture
def extraits(monkeypatch):
    """Remplace la lecture des CSV par trois tables minuscules."""

    def poser(code_sondage, cible="Oui"):
        tables = {
            "extrait_sirh.csv": pd.DataFrame({"id_employee": [1, 2]}),
            "extrait_eval.csv": pd.DataFrame({"eval_number": ["a", "b"]}),
            "extrait_sondage.csv": pd.DataFrame(
                {
                    "code_sondage": code_sondage,
                    "a_quitte_l_entreprise": [cible, "Non"],
                }
            ),
        }
        monkeypatch.setattr(
            train_model.pd, "read_csv", lambda chemin: tables[chemin.name]
        )

    return poser


def test_des_extraits_decales_font_echouer_le_chargement(extraits):
    """Un decalage d'une ligne entrainerait le modele sur de fausses associations."""
    extraits(code_sondage=[2, 1])
    with pytest.raises(ValueError, match="ne correspondent pas"):
        train_model.charger_donnees()


def test_une_cible_inconnue_fait_echouer_le_chargement(extraits):
    """Sans ce garde-fou, la valeur devient NaN et disparait silencieusement."""
    extraits(code_sondage=[1, 2], cible="Peut-etre")
    with pytest.raises(ValueError, match="Valeurs de cible inconnues"):
        train_model.charger_donnees()
