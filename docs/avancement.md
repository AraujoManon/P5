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
- dépendances déclarées dans `pyproject.toml` : `dependencies` pour la
  production, `optional-dependencies.dev` pour les tests et ruff
- `[project.scripts]` installe cinq commandes (`attrition-api`,
  `attrition-creer-base`…) : l'hébergeur lance `attrition-api`, il n'a pas
  à connaître l'arborescence du dépôt
- versions épinglées avec `==`
- `.venv` créé, 43 paquets installés (`pip install -e ".[dev]"`)

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

### Étape 2 — pipeline et entraînement ✅

Commits `ae79d03` et `667e0f5`

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

### Étape 3 — schémas Pydantic ✅

Commit `f9f3175`, fusionné dans `main` par `5074cc5`

`src/schemas.py` définit le contrat de l'API :

- `EmployeEntree` — les 26 champs, dans l'ordre de `COLONNES_ENTREE`.
  19 numériques bornés par l'helper `borne()`, qui lit `BORNES` dans
  `features.py` plutôt que de redéclarer les mêmes valeurs ici.
  7 champs texte en `Literal`, dont les modalités sont recopiées à la main.
- `PredictionSortie` — `probabilite_demission`, `prediction` en Oui/Non,
  et `seuil_applique`.

`extra="forbid"` : un champ inconnu est refusé au lieu d'être ignoré. Sans ça,
`"agee": 41` passerait sans bruit et `age` manquerait plus loin, avec une
erreur bien moins lisible.

Le seuil est renvoyé avec la réponse. Il vaut 0.40, pas 0.50 : sans lui, une
probabilité de 0.45 associée à « Oui » ressemble à un bug.

Un exemple d'employé (le salarié n°1 des CSV, un vrai départ) est déclaré dans
`json_schema_extra`. Il remplit le formulaire « Try it out » de Swagger.

**Décision** : les modalités sont écrites deux fois, dans `features.py` et dans
`schemas.py`. Un `Literal` est lu à la construction de la classe, donc le
construire depuis `MODALITES` donnerait un fichier illisible et une doc Swagger
qu'on ne peut plus relire. On garde la recopie, et un test la surveille.

### Étape 3 bis — premiers tests ✅

Même commit. `tests/test_schemas.py`, 6 tests :

| | Vérifie que… |
|---|---|
| 1 | les 26 champs déclarés sont exactement `COLONNES_ENTREE` |
| 2 | les 7 `Literal` correspondent à `MODALITES` — c'est le garde-fou de la recopie |
| 3 | l'exemple de la doc Swagger est valide |
| 4 | trois entrées fautives sont refusées : hors borne, modalité inconnue, champ en trop |

Le test 4 est écrit avec `@pytest.mark.parametrize`, donc les trois cas
apparaissent séparément dans le rapport.

### Étape 4 — API FastAPI ✅

`src/main.py` expose deux routes.

`GET /health` renvoie `{"statut": "ok", "modele_charge": true}`. Le second
champ teste la présence réelle du pipeline en mémoire : une route qui
répondrait « ok » en dur dirait que tout va bien même avec un `.joblib`
manquant au déploiement.

`POST /predict` prend un `EmployeEntree`, le convertit en DataFrame d'une
ligne, appelle `predict_proba` et compare au seuil.

Le modèle est chargé une seule fois, au démarrage, par le `lifespan` de
FastAPI. Le charger dans la route relirait 1,2 Mo depuis le disque à chaque
requête.

Trois détails qui comptent :

- `pd.DataFrame([employe.model_dump()])` — les crochets font une liste d'une
  ligne, donc un tableau 1 × 26. Sans eux, le dictionnaire donnerait un
  tableau d'une seule colonne.
- `[0, 1]` sur la sortie de `predict_proba` : première ligne, colonne de la
  classe 1. La cible étant encodée en 0/1 par `MAPPING_CIBLE`, la classe 1
  est bien « est parti ». C'est le même indice que dans `train_model.py`.
- `float(...)` explicite : `predict_proba` renvoie un `numpy.float64`, qui se
  sérialise mal en JSON selon les versions.

`SEUIL_DECISION` est importé de `pipeline.py`, pas réécrit ici. Le seuil
existe à un seul endroit dans tout le projet.

### Étape 4 bis — tests des routes ✅

`tests/test_api.py`, 3 tests, écrits dans le même commit que les routes.

| | Vérifie que… |
|---|---|
| 1 | `/health` répond 200 et que le modèle est bien chargé |
| 2 | `/predict` répond 200, probabilité dans [0, 1], décision cohérente avec le seuil |
| 3 | un champ inconnu donne une 422 |

`with TestClient(app) as client` : le `with` n'est pas décoratif, c'est lui
qui déclenche le `lifespan`, donc le chargement du modèle. Sans lui, `modele`
reste vide et le test échoue alors que le code est bon.

Le test 2 ne compare à aucune valeur en dur. La probabilité de l'exemple vaut
0.83 aujourd'hui, mais elle bougera au prochain réentraînement : un test qui
exigerait ce chiffre casserait sans qu'il y ait de bug, et un test qui casse
sans raison finit par être ignoré. Il vérifie donc les propriétés vraies quel
que soit le modèle.

Le test 3 envoie l'exemple valide **plus** un champ `agee`. Une seule chose
change par rapport au cas qui passe, donc la 422 ne peut venir que de là.

**Couverture** : 94 % sur `src/` (`pytest --cov=src`). `main.py` et
`schemas.py` à 100 %, `pipeline.py` à 75 % — les lignes non couvertes sont
celles de `construire_pipeline()`, appelée à l'entraînement et pas par l'API.

### Étape 5 — PostgreSQL ✅

Le détail du schéma et les choix de modélisation sont dans
[`base_de_donnees.md`](base_de_donnees.md). Ici, ce que l'étape a appris.

Quatre tables : `employes_sirh`, `employes_sondage`, `employes_eval` pour le
jeu de données, `predictions` pour la traçabilité. Trois tables plutôt qu'une
parce que les données viennent de trois extraits distincts, et que l'UML doit
montrer cette réalité.

`src/database.py` porte la requête d'insertion, `get_session()` et
`enregistrer_prediction()`. La route reçoit sa session par `Depends`, donc
FastAPI l'ouvre et la referme, y compris si la route plante.

**Le moteur n'est créé qu'à la première requête**, pas à l'import du module.
C'est ce qui permet à pytest de tourner sans PostgreSQL : les tests remplacent
`get_session` par une `SessionFactice` via `app.dependency_overrides`. Sans ce
choix, la CI de l'étape 7 aurait besoin d'une base juste pour lancer 10 tests.

Pas de `try/except` autour de l'enregistrement. Une prédiction renvoyée sans
avoir été tracée casse en silence la promesse « tout passe par la base ».
Mieux vaut une erreur visible.

**Deux pièges rencontrés.**

Le `%` du commentaire `"11 %"` dans `schema.sql` faisait planter psycopg :
`only '%s', '%b', '%t' are allowed as placeholders`. Le pilote lit le `%`
comme un paramètre de requête, même à l'intérieur d'un commentaire.
Commentaire reformulé sans le symbole.

`eval_number` n'est pas un entier mais `E_1`, `E_2`, `E_4`. C'est
`"E_" + id_employee`, vérifié sur les 1470 lignes. La table garde
`eval_number` en texte et porte en plus `id_employee` pour la clé étrangère.
La déclaration en `integer` venait d'une supposition, pas d'une lecture des
données — le genre d'erreur qu'un simple coup d'œil au CSV évite.

**Vérifications**

```
employes_sirh 1470 | employes_sondage 1470 | employes_eval 1470
jointure des 3 tables : 1470 lignes, aucun employe perdu
taux de depart : 16,1 %   (le chiffre de l'enonce)
```

Un appel réel à `/predict` écrit bien sa ligne, relisible en SQL :

```
id 1 | 2026-09-04 10:07+02 | 0.8300 | Oui | 0.40 | 0.1.0
```

`scripts/scorer_base.py` fait tourner le modèle sur les 1470 employés depuis
la base : 738 signalés à risque. Attention à ne pas lire ce chiffre comme une
performance — ces employés étaient dans le jeu d'entraînement, le modèle les
connaît déjà.

Couverture après l'étape : **90 %** (`database.py` à 62 %, les branches non
couvertes sont la création réelle du moteur).

### Authentification ✅

`src/securite.py`. Une clé d'API dans l'en-tête `X-API-Key`, comparée à la
variable `API_KEY`. `/predict` la réclame, `/health` non : la supervision et
Hugging Face doivent pouvoir vérifier que le service tourne sans détenir de
secret.

Pourquoi une clé et pas un JWT : le client est un outil RH, pas un humain qui
se connecte. Il n'y a pas de notion d'utilisateur dans la base, donc une table
de comptes et de mots de passe répondrait à un besoin qui n'existe pas. Une clé
se range dans un coffre à secrets, ce que l'étape CI/CD demande de montrer.

Deux détails qui se défendent à l'oral :

`secrets.compare_digest` au lieu de `==`. Une comparaison normale s'arrête au
premier caractère faux, donc son temps de réponse dit combien de caractères
étaient justes. Sur un grand nombre d'essais, ça permet de reconstituer la clé.
`compare_digest` prend toujours le même temps.

`auto_error=False` sur `APIKeyHeader`. Par défaut FastAPI renvoie un 403 quand
l'en-tête manque, ce qui veut dire « connu mais interdit ». Ici il n'est pas
connu du tout : 401.

La clé locale est dans `.env`, jamais versionnée. `.env.example` indique
comment en générer une.

---

## Ce qu'il reste

### Étape 6 — tests

Commencé aux étapes 3 et 4 : `test_schemas.py` et `test_api.py`,
9 tests, 94 % de couverture. Reste à couvrir `features.py` et `pipeline.py`
directement, et à produire le rapport de couverture en fichier livrable.

Le fichier de test est écrit en même temps que le code qu'il teste, pas dans un
passage groupé à la fin : le garde-fou des modalités n'aurait aucun sens écrit
trois semaines après la recopie qu'il surveille.

### Étape 7 — CI/CD

GitHub Actions. Tests automatiques à chaque push, gestion des secrets,
déploiement sur Hugging Face Spaces. Le pipeline doit rester sous 10 minutes.

Prévoir un test de non-régression du modèle basé sur le rappel en validation
croisée, pas sur la mesure du jeu de test qui est trop instable.

### Étape 8 — documentation

README complet (installation, utilisation, déploiement, authentification,
sécurité), documentation de l'API, documentation technique du modèle.

### Transverse

- tags de version au fil des étapes
- support de présentation pour la soutenance

---

## Méthode de travail

Une branche par étape, un commit par bloc cohérent, convention
*Conventional Commits* (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).

Le flux, à chaque étape :

```powershell
git switch -c feat/nom-de-l-etape
# ... code, puis ruff, puis pytest
git commit -m "feat: ..."
git switch main
git merge --no-ff feat/nom-de-l-etape
git branch -d feat/nom-de-l-etape
git push
```

`--no-ff` force un commit de fusion. Sans lui, git avance simplement le
pointeur et la branche ne laisse aucune trace dans le graphe — on perd
justement ce que le livrable demande de montrer.

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
