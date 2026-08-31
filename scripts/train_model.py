"""Entraine le modele et sauvegarde le pipeline complet.

Lancement :
    python -m scripts.train_model

Produit deux fichiers dans models/ :
    attrition_model.joblib  le pipeline entier (preparation + encodage + modele)
    metrics.json            les performances, pour la doc et pour la CI
"""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split

from src.features import COLONNE_CIBLE, MAPPING_CIBLE
from src.pipeline import GRAINE, SEUIL_DECISION, construire_pipeline

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_DATA = RACINE / "data"
DOSSIER_MODELS = RACINE / "models"

FICHIER_MODELE = DOSSIER_MODELS / "attrition_model.joblib"
FICHIER_METRIQUES = DOSSIER_MODELS / "metrics.json"


def charger_donnees():
    """Recolle les 3 CSV et sort (X brut, y en 0/1).

    Les fichiers sont alignes ligne a ligne. On le verifie avec id_employee
    et code_sondage au lieu de le supposer.
    """
    df_sirh = pd.read_csv(DOSSIER_DATA / "extrait_sirh.csv")
    df_eval = pd.read_csv(DOSSIER_DATA / "extrait_eval.csv")
    df_sondage = pd.read_csv(DOSSIER_DATA / "extrait_sondage.csv")

    df = pd.concat([df_sirh, df_eval, df_sondage], axis=1)

    if not (df["id_employee"] == df["code_sondage"]).all():
        raise ValueError(
            "Les identifiants ne correspondent pas entre les extraits : "
            "les fichiers ne sont pas alignes ligne a ligne."
        )

    y = df[COLONNE_CIBLE].map(MAPPING_CIBLE)
    if y.isna().any():
        valeurs = df.loc[y.isna(), COLONNE_CIBLE].unique()
        raise ValueError(f"Valeurs de cible inconnues : {list(valeurs)}")

    return df, y


def evaluer(modele, X_test, y_test, seuil):
    """Metriques au seuil donne.

    On passe par predict_proba() et pas predict(), qui est bloque a 0.50.
    """
    proba = modele.predict_proba(X_test)[:, 1]
    y_pred = (proba >= seuil).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()

    return {
        "seuil": seuil,
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_test, y_pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_test, proba), 4),
        "matrice_confusion": {
            "vrais_negatifs": int(tn),
            "faux_positifs": int(fp),
            "faux_negatifs": int(fn),
            "vrais_positifs": int(tp),
        },
        "departs_detectes": f"{int(tp)}/{int(tp + fn)}",
    }


def valider_croise(X_train, y_train, seuil, n_plis=5):
    """Rappel moyen en validation croisee stratifiee, au seuil retenu.

    Le jeu de test ne contient que 47 departs : un employe de plus ou de moins
    change le rappel de 2 points. En ne changeant que la graine, il varie entre
    0.81 et 0.89. Une seule mesure ne dit donc pas grand-chose, d'ou la CV.

    Boucle ecrite a la main parce que cross_val_score passe par predict(),
    bloque a 0.50, alors qu'on veut mesurer a 0.40.
    """
    skf = StratifiedKFold(n_splits=n_plis, shuffle=True, random_state=GRAINE)
    rappels = []

    for i_train, i_valid in skf.split(X_train, y_train):
        modele = construire_pipeline()
        modele.fit(X_train.iloc[i_train], y_train.iloc[i_train])
        proba = modele.predict_proba(X_train.iloc[i_valid])[:, 1]
        y_pred = (proba >= seuil).astype(int)
        rappels.append(recall_score(y_train.iloc[i_valid], y_pred, zero_division=0))

    rappels = pd.Series(rappels)
    return {
        "n_plis": n_plis,
        "seuil": seuil,
        "rappel_moyen": round(float(rappels.mean()), 4),
        "ecart_type": round(float(rappels.std()), 4),
        "par_pli": [round(float(r), 4) for r in rappels],
    }


def main():
    X, y = charger_donnees()
    print(f"Donnees : {len(X)} lignes, {y.sum()} departs ({y.mean():.1%})")

    # stratify=y garde les 16 % de departs des deux cotes du split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=GRAINE, stratify=y
    )
    print(f"Train : {len(X_train)} lignes | Test : {len(X_test)} lignes")

    # La CV ne touche pas au jeu de test, elle redecoupe juste le train
    print("\nValidation croisee en cours...")
    cv = valider_croise(X_train, y_train, SEUIL_DECISION)
    print(
        f"  rappel {cv['rappel_moyen']} +/- {cv['ecart_type']} sur {cv['n_plis']} plis (seuil {cv['seuil']})"
    )
    print(f"  par pli : {cv['par_pli']}")

    modele = construire_pipeline()
    modele.fit(X_train, y_train)
    print("\nEntrainement termine")

    metriques_seuil = evaluer(modele, X_test, y_test, SEUIL_DECISION)
    metriques_defaut = evaluer(modele, X_test, y_test, 0.50)

    print(f"\n--- Seuil retenu {SEUIL_DECISION} ---")
    print(f"  rappel     {metriques_seuil['recall']}")
    print(f"  precision  {metriques_seuil['precision']}")
    print(f"  departs    {metriques_seuil['departs_detectes']}")
    print(f"  fausses alertes {metriques_seuil['matrice_confusion']['faux_positifs']}")

    print("\n--- Seuil par defaut 0.50, pour comparaison ---")
    print(f"  rappel     {metriques_defaut['recall']}")
    print(f"  precision  {metriques_defaut['precision']}")
    print(f"  departs    {metriques_defaut['departs_detectes']}")

    DOSSIER_MODELS.mkdir(exist_ok=True)
    joblib.dump(modele, FICHIER_MODELE)

    rapport = {
        "seuil_retenu": SEUIL_DECISION,
        "graine": GRAINE,
        "nb_lignes_total": len(X),
        "nb_lignes_train": len(X_train),
        "nb_lignes_test": len(X_test),
        "taux_depart": round(float(y.mean()), 4),
        "validation_croisee": cv,
        "au_seuil_retenu": metriques_seuil,
        "au_seuil_par_defaut": metriques_defaut,
    }
    FICHIER_METRIQUES.write_text(
        json.dumps(rapport, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    taille = FICHIER_MODELE.stat().st_size / 1024
    print(f"\nModele sauvegarde : {FICHIER_MODELE.name} ({taille:.0f} Ko)")
    print(f"Metriques         : {FICHIER_METRIQUES.name}")


if __name__ == "__main__":
    main()
