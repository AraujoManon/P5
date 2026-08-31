# Avancement du projet

Journal de bord. Mis à jour au fur et à mesure.

---

## Le projet en bref

**Client fictif** : TechNova Partners (aussi appelé Futurisys dans l'énoncé).
16 % de démissions par an.

**Ce qu'on fait** : le modèle de prédiction du risque de démission développé en
P4 vit dans un notebook, donc inutilisable au quotidien. On le transforme en
service : une API REST, une base PostgreSQL qui trace tout, des tests, un
pipeline CI/CD.

**Le P4 de référence** : https://github.com/AraujoManon/P4-attrition-technova
(notebook `P4_final.ipynb`, 68 cellules de code)

**Ce dépôt** : https://github.com/AraujoManon/P5

---

## Décisions prises

| Sujet | Décision | Pourquoi |
|---|---|---|
| Repartir de zéro | oui, ancien dépôt supprimé | réécrire pour comprendre ce qu'on soutient |
| Fautes de frappe du CSV (`augementation`, `annes`) | on les garde | éviter une table de correspondance CSV ↔ API, qu'un oubli rendrait fausse silencieusement |
| Modèle | RandomForest + RandomUnderSampler, `random_state=42` | c'est ce que le P4 a retenu après comparaison de 4 approches |
| Hyperparamètres | valeurs par défaut | le P4 avait lancé un `RandomizedSearchCV` mais n'a pas appliqué `best_params_` |
| Seuil de décision | 0.40 | arbitrage métier du P4 : un départ manqué coûte ~10× une fausse alerte |
| Encodage | `OneHotEncoder` dans le pipeline, pas `get_dummies` | `get_dummies` sur 1 employé ne produit pas les bonnes colonnes |
| Mise à l'échelle | aucune | un RandomForest coupe sur des seuils, pas sur des distances |
| Mesure de référence | validation croisée 5 plis | le jeu de test n'a que 47 départs, une mesure unique est instable |

---

## Ce qui est fait

### Étape 0 — structure et environnement ✅

Commit `6c7239a`

```
data/       les 3 CSV sources (1470 lignes chacun)
src/        code de l'application
tests/      tests pytest
scripts/    entraînement, création BDD
sql/        schéma PostgreSQL
docs/       documentation
models/     le .joblib et les métriques
```

- `.gitignore` créé **avant** le premier commit (`.venv`, `__pycache__`, `.env`)
- `.gitattributes` : fins de ligne en LF, pour que la CI Linux soit d'accord
- `requirements.txt` (production) et `requirements-dev.txt` (tests, ruff)
- versions épinglées avec `==`
- `.venv` créé, 43 paquets installés

**Piège rencontré** : `pip` échouait avec
`Could not find a suitable TLS CA certificate bundle`. Cause : l'installeur
PostgreSQL 17 a défini une variable système `CURL_CA_BUNDLE` pointant vers un
fichier qui n'existe pas. Contournement : `$env:CURL_CA_BUNDLE = ""` avant le
`pip install`.

### Étape 1 — contrat de données ✅

Commits `b4a6680` et `2d5c37e` — voir [`features.md`](features.md)

`src/features.py` : les 26 colonnes d'entrée, leurs bornes, les modalités
autorisées, les 7 colonnes écartées avec leur motif, et les fonctions de
préparation (`preparer_donnees`, `creer_features_metier`, etc.).

Vérifié sur les 1470 lignes : 26 + 7 écartées + 1 cible = 34 colonnes CSV,
modalités conformes, aucun NaN, pas de division par zéro, fonctionne aussi bien
sur 1 ligne que sur le fichier entier.

### Étape 2 — pipeline et entraînement ⏳ pas encore commité

`src/pipeline.py` — 4 étapes :

```
preparer_donnees → OneHotEncoder (6 nominales) → RandomUnderSampler → RandomForest
```

`scripts/train_model.py` — charge les CSV, split stratifié 80/20, validation
croisée, entraînement, évaluation aux seuils 0.40 et 0.50, sauvegarde.

Produit `models/attrition_model.joblib` (1,2 Mo) et `models/metrics.json`.

**Résultats**

```
Validation croisee 5 plis, seuil 0.40
  rappel 0.826 +/- 0.063
  par pli : 0.763 | 0.789 | 0.895 | 0.895 | 0.789

Jeu de test (294 lignes, 47 departs), seuil 0.40
  rappel 0.787  (37/47)
  precision 0.234
  121 fausses alertes
  ROC AUC 0.739
```

Le P4 annonçait un rappel de 0.85. L'écart n'est pas une régression : en faisant
seulement varier la graine aléatoire, le rappel va de 0.81 à 0.89 sur ce même
jeu de test. La validation croisée (0.83 ± 0.06) recouvre le chiffre du P4.

À retenir pour la soutenance : **l'accuracy tombe à 0.55** au seuil 0.40. C'est
normal, et c'est pour ça qu'on ne la regarde pas. Un modèle qui répondrait
« personne ne part » obtiendrait 84 % d'accuracy en ne servant à rien.

---

## Ce qu'il reste

### Étape 3 — schémas Pydantic

`src/schemas.py`. Un modèle Pydantic pour l'entrée (26 champs, bornes et
modalités importées de `features.py`) et un pour la sortie
(`probabilite_demission`, `prediction`, `seuil_applique`).

### Étape 4 — API FastAPI

`src/main.py` et les routes. Au minimum `POST /predict` et `GET /health`.
Documentation Swagger automatique. Chargement du `.joblib` au démarrage, pas à
chaque requête.

### Étape 5 — PostgreSQL

Schéma des tables, script de création (`.sql` ou `create_db.py`), insertion du
dataset complet, enregistrement systématique des entrées et sorties du modèle.
Un schéma UML de la base. Des scripts pour interroger les données.

PostgreSQL 17 est déjà installé sur la machine.

### Étape 6 — tests

Tests unitaires et fonctionnels avec pytest, rapport de couverture avec
pytest-cov. Couvrir les cas critiques et les scénarios d'erreur (modalité
inconnue, champ manquant, valeur hors bornes).

### Étape 7 — CI/CD

GitHub Actions. Tests automatiques à chaque push, gestion des secrets,
déploiement sur Hugging Face Spaces. Le pipeline doit rester sous 10 minutes.

Prévoir un test de non-régression du modèle basé sur le rappel en validation
croisée, pas sur la mesure du jeu de test qui est trop instable.

### Étape 8 — documentation

README complet (installation, utilisation, déploiement, authentification,
sécurité), documentation de l'API, documentation technique du modèle.

### Transverse

- authentification et sécurisation de l'API
- tags de version au fil des étapes
- support de présentation pour la soutenance

---

## Méthode de travail

Une branche par étape, un commit par bloc cohérent, convention
*Conventional Commits* (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).

Après chaque fichier écrit, vérifier qu'il est bien sur le disque :

```powershell
Get-ChildItem src
```

Un fichier à `0` octet n'a rien dedans, quoi que l'éditeur affiche.

Avant chaque commit :

```powershell
python -m ruff check src/ scripts/
python -m ruff format src/ scripts/
```
