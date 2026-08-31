"""Pipeline sklearn : preparation + encodage + modele en un seul objet.

Tout est sauvegarde ensemble dans models/attrition_model.joblib. L'API charge
ce fichier et appelle predict_proba() sur des donnees brutes, sans rien
transformer elle-meme.

En P4 le One Hot etait fait avec pd.get_dummies() sur le jeu complet. Ca ne
marche pas dans une API : sur un seul employe, get_dummies ne cree que les
colonnes des modalites presentes dans cette ligne. Un "Consultant" donnerait
une seule colonne poste_* au lieu des 8 attendues. Un OneHotEncoder entraine
garde en memoire toutes les modalites vues, donc il sort toujours les memes
colonnes dans le meme ordre.
"""

from imblearn.pipeline import Pipeline
from imblearn.under_sampling import RandomUnderSampler
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder

from src.features import COLONNES_NOMINALES, preparer_donnees

SEUIL_DECISION = 0.40
GRAINE = 42


def construire_pipeline():
    """Assemble les 4 etapes du pipeline, sans l'entrainer.

    preparation  -> nettoyage, encodage ordinal, features metier
    encodage     -> One Hot sur les 6 colonnes nominales
    undersampler -> reequilibre les classes, uniquement a l'entrainement
    rf           -> RandomForest, comme en P4
    """
    preparation = FunctionTransformer(preparer_donnees, validate=False)

    encodage = ColumnTransformer(
        transformers=[
            (
                "onehot",
                # drop="first" = le drop_first=True du notebook.
                # handle_unknown="error" fait planter si une modalite inconnue
                # arrive, plutot que de sortir une ligne de zeros qui donnerait
                # une prediction fausse sans prevenir.
                OneHotEncoder(
                    drop="first", handle_unknown="error", sparse_output=False
                ),
                COLONNES_NOMINALES,
            )
        ],
        # Le reste passe tel quel. Pas de StandardScaler : un RandomForest
        # coupe sur des seuils, la mise a l'echelle ne lui sert a rien.
        remainder="passthrough",
        verbose_feature_names_out=False,
    )

    return Pipeline(
        steps=[
            ("preparation", preparation),
            ("encodage", encodage),
            ("undersampler", RandomUnderSampler(random_state=GRAINE)),
            ("rf", RandomForestClassifier(random_state=GRAINE)),
        ]
    )
