from typing import get_args

import pytest

from src.features import COLONNES_ENTREE, MODALITES
from src.schemas import EmployeEntree

from pydantic import ValidationError


def test_les_champs_correspondent_au_contrat():
    assert list(EmployeEntree.model_fields) == COLONNES_ENTREE


def test_les_modalites_correspondent_au_contrat():
    for nom, valeurs in MODALITES.items():
        assert list(get_args(EmployeEntree.model_fields[nom].annotation)) == valeurs


def test_l_exemple_de_la_doc_est_valide():
    exemple = EmployeEntree.model_json_schema()["example"]
    EmployeEntree(**exemple)


@pytest.mark.parametrize(
    "champ, valeur",
    [
        ("age", 5),  # sous la borne
        ("poste", "Stagiaire"),  # modalité inconnue
        ("agee", 41),  # champ en trop
    ],
)
def test_une_entree_invalide_est_refusee(champ, valeur):
    donnees = dict(EmployeEntree.model_json_schema()["example"])
    donnees[champ] = valeur
    with pytest.raises(ValidationError):
        EmployeEntree(**donnees)
