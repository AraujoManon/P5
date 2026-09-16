"""Tests des garde-fous du scorer par lot."""

import pandas as pd

from scripts import scorer_base
from src.database import INSERTION
from src.pipeline import SEUIL_DECISION

ENTREES = pd.DataFrame([{"age": 30}, {"age": 45}])


def test_le_scorer_fournit_tous_les_parametres_de_l_insertion():
    """Un parametre oublie ne se voit qu'a l'execution, sur la vraie base."""
    ligne = scorer_base.fabriquer_lignes(ENTREES, [0.9, 0.1])[0]
    assert set(ligne) == set(INSERTION.compile().binds)


def test_le_scorer_decide_au_seuil_du_service():
    """Le scorer et l'API doivent trancher au meme endroit : pile au seuil, c'est Oui."""
    lignes = scorer_base.fabriquer_lignes(
        ENTREES, [SEUIL_DECISION, SEUIL_DECISION - 0.01]
    )
    assert [ligne["prediction"] for ligne in lignes] == ["Oui", "Non"]
