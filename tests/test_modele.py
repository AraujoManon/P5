"""Non-regression du modele livre : il doit valoir ce qu'on a mesure."""

import json
from pathlib import Path

from src.pipeline import SEUIL_DECISION

METRIQUES = json.loads(
    (Path(__file__).resolve().parent.parent / "models" / "metrics.json").read_text(
        encoding="utf-8"
    )
)

# Mesure au dernier entrainement : 0.8263, ecart-type 0.0634 sur 5 plis.
# Le plancher laisse un ecart-type de marge, sinon le bruit ferait rougir la CI.
PLANCHER_RAPPEL = 0.75


def test_le_rappel_en_validation_croisee_ne_decroche_pas():
    """Le rappel des 5 plis, pas celui du jeu de test : 47 departs, trop instable."""
    assert METRIQUES["validation_croisee"]["rappel_moyen"] >= PLANCHER_RAPPEL


def test_le_seuil_mesure_est_celui_que_l_api_applique():
    """Sinon les chiffres du dossier decrivent un modele qui n'est plus servi."""
    assert METRIQUES["seuil_retenu"] == SEUIL_DECISION
