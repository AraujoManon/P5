"""Tests de la structure du pipeline et du comportement de l'undersampler."""

import pandas as pd
import pytest

from src.features import COLONNES_NOMINALES
from src.pipeline import construire_pipeline
from src.schemas import EmployeEntree

EXEMPLE = EmployeEntree.model_config["json_schema_extra"]["example"]


@pytest.fixture
def jeu_desequilibre():
    """4 employes, un seul depart : de quoi donner du travail a l'undersampler."""
    X = pd.DataFrame([EXEMPLE] * 4)
    y = pd.Series([0, 0, 0, 1])
    return X, y


def test_les_quatre_etapes_sont_dans_l_ordre():
    """L'undersampler apres l'encodage : l'inverse donnerait un autre modele."""
    etapes = [nom for nom, _ in construire_pipeline().steps]
    assert etapes == ["preparation", "encodage", "undersampler", "rf"]


def test_le_onehot_refuse_une_modalite_inconnue():
    """handle_unknown="error" : mieux vaut planter qu'une ligne de zeros silencieuse."""
    _, encodeur, colonnes = (
        construire_pipeline().named_steps["encodage"].transformers[0]
    )
    assert encodeur.handle_unknown == "error"
    assert colonnes == COLONNES_NOMINALES


def test_le_onehot_laisse_tomber_la_premiere_modalite():
    """Equivalent du drop_first=True du notebook P4."""
    _, encodeur, _ = construire_pipeline().named_steps["encodage"].transformers[0]
    assert encodeur.drop == "first"


def test_l_undersampler_ne_s_applique_pas_a_la_prediction(jeu_desequilibre):
    """C'est ce qui justifie la Pipeline d'imblearn plutot que celle de sklearn.

    A l'entrainement il reequilibre les classes. A la prediction il doit etre
    transparent : 4 employes en entree, 4 predictions en sortie.
    """
    X, y = jeu_desequilibre
    pipeline = construire_pipeline().fit(X, y)
    assert len(pipeline.predict(X)) == len(X)
