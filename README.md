# API de prédiction du risque de démission

Service REST qui expose le modèle d'attrition de TechNova Partners. On lui
envoie les 26 informations d'un salarié, il renvoie une probabilité de départ
et une décision. Chaque appel est enregistré en base.

Le modèle vient du projet P4, où il vivait dans un notebook. Ici il devient un
service utilisable au quotidien par les RH : validé, testé, tracé, déployable.

## Prérequis

- Python 3.13
- PostgreSQL 17

## Installation

```powershell
git clone https://github.com/AraujoManon/P5.git
cd P5
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

L'installation en `-e` (éditable) n'est pas un détail : `src/main.py` cherche
le modèle en remontant d'un dossier depuis sa propre position. Une installation
classique copierait `src/` dans `site-packages`, loin de `models/`.

`[dev]` ajoute pytest, pytest-cov, httpx et ruff. Sans ce suffixe, seules les
dépendances d'exécution sont installées.

Si `pip install` échoue sur « Could not find a suitable TLS CA certificate
bundle », c'est l'installateur PostgreSQL de Windows qui a posé une variable
`CURL_CA_BUNDLE` pointant vers un fichier qui n'existe pas. Contournement
immédiat :

```powershell
Remove-Item Env:\CURL_CA_BUNDLE
```

Durablement, supprimer cette variable dans les variables d'environnement
utilisateur de Windows.

## Configuration

Copier `.env.example` en `.env` et remplir les trois variables :

| Variable | À quoi elle sert |
|---|---|
| `DATABASE_URL` | connexion à la base `attrition`, utilisée par l'API |
| `DATABASE_ADMIN_URL` | connexion au serveur PostgreSQL, pour créer la base |
| `API_KEY` | clé de service attendue dans l'en-tête `X-API-Key` |
| `JWT_SECRET` | clé de signature des jetons d'accès |

Générer une clé ou un secret (la même commande sert aux deux) :

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

`.env` est dans `.gitignore` et n'est jamais versionné. En production, ces
trois valeurs sont des variables d'environnement fournies par l'hébergeur.

## Mettre en place la base

```powershell
attrition-creer-base
```

Crée la base, ses quatre tables et y charge les trois extraits CSV. La commande
est rejouable : elle supprime et recrée les tables à chaque exécution. Le détail
du schéma est dans [`docs/base_de_donnees.md`](docs/base_de_donnees.md).

## Entraîner le modèle

```powershell
attrition-entrainer
```

Produit `models/attrition_model.joblib` et `models/metrics.json`. Le dépôt
contient déjà un modèle entraîné : cette commande ne sert que si les données
ou le pipeline changent.

## Lancer l'API

```powershell
attrition-api
```

L'API écoute sur le port 8000, ou sur celui que donne la variable `PORT`.

- documentation interactive : http://127.0.0.1:8000/docs
- état du service : http://127.0.0.1:8000/health

## Appeler l'API

Avec la clé de service :

```powershell
$corps = Get-Content docs/exemple.json -Raw
Invoke-RestMethod -Uri http://127.0.0.1:8000/predict -Method Post `
  -Headers @{ "X-API-Key" = $env:API_KEY } `
  -ContentType "application/json" -Body $corps
```

Avec un compte utilisateur :

```powershell
$jeton = (Invoke-RestMethod -Uri http://127.0.0.1:8000/token -Method Post `
  -Body @{ username = "martine"; password = "..." }).access_token

Invoke-RestMethod -Uri http://127.0.0.1:8000/predict -Method Post `
  -Headers @{ Authorization = "Bearer $jeton" } `
  -ContentType "application/json" -Body $corps
```

Réponse :

```json
{
  "probabilite_demission": 0.83,
  "prediction": "Oui",
  "seuil_applique": 0.4
}
```

Le détail des routes, des champs attendus et des codes d'erreur est dans
[`docs/api.md`](docs/api.md).

## Authentification et gestion des accès

Deux méthodes, parce qu'il y a deux sortes d'appelants.

**Les comptes utilisateurs**, pour les humains. On envoie son identifiant et
son mot de passe à `/token`, on reçoit un jeton valable trente minutes, et on
le présente ensuite dans l'en-tête `Authorization: Bearer <jeton>`. Créer un
compte, ou changer son mot de passe :

```powershell
attrition-creer-utilisateur martine
```

Le mot de passe est saisi sans écho, douze caractères minimum, et n'est jamais
stocké : seul son hachage bcrypt part en base.

**La clé de service**, pour l'outil RH. Un automate n'a pas de mot de passe à
saisir ni de session à renouveler : il présente son en-tête `X-API-Key`. Faire
tourner un compte utilisateur dans un programme reviendrait à y écrire un mot
de passe en dur, ce qui est exactement ce qu'on cherche à éviter.

Dans les deux cas, l'appelant identifié est écrit dans la colonne `appelant`
de la table `predictions` : on sait qui a demandé quoi. `/health`, lui,
n'exige rien — la supervision et l'hébergeur doivent pouvoir vérifier que le
service tourne sans détenir de secret.

### Les bonnes pratiques appliquées

**Les mots de passe sont hachés, pas chiffrés.** Un chiffrement se déchiffre ;
un hachage, non. bcrypt tire en plus un sel aléatoire par mot de passe, donc
deux comptes ayant choisi le même mot de passe ont deux hachages différents, et
une table de hachages précalculés ne sert à rien. Son coût de calcul est
volontairement élevé, ce qui rend l'essai systématique de millions de
combinaisons beaucoup trop lent pour être rentable.

**Les échecs d'authentification se ressemblent tous.** Compte inconnu, mot de
passe faux, compte désactivé : même code, même message. Et quand le compte
n'existe pas, un hachage leurre est quand même comparé — sans lui, une réponse
instantanée signalerait que l'identifiant n'existe pas, et il suffirait de
mesurer le temps de réponse pour dresser la liste des comptes réels.

**La clé d'API est comparée en temps constant.** Une comparaison ordinaire
s'arrête au premier caractère faux, donc sa durée trahit le nombre de
caractères justes ; sur un grand nombre d'essais, la clé se reconstitue.

**Les jetons expirent au bout de trente minutes** et sont signés. Un jeton
intercepté ne vaut pas éternellement, et un jeton fabriqué sans le secret est
rejeté.

**Un refus donne 401, pas 403.** 403 signifie « je sais qui tu es, mais c'est
interdit ». Ici on ne sait rien du demandeur.

**Les secrets ne sont pas dans le dépôt.** `API_KEY`, `JWT_SECRET` et
`DATABASE_URL` sont des variables d'environnement : un fichier `.env` ignoré
par git en développement, les secrets de la plateforme en production. Aucun mot
de passe n'apparaît dans les journaux ni dans la table des prédictions.

## Tests

```powershell
pytest
```

51 tests, 100 % de couverture sur `src/`. La couverture est activée par défaut
dans `pyproject.toml`, il n'y a rien à ajouter à la commande.

Pour le rapport détaillé en HTML :

```powershell
pytest --cov-report=html
start htmlcov/index.html
```

`htmlcov/` n'est pas versionné : un rapport se régénère. La CI en publie un
à chaque exécution, téléchargeable depuis l'onglet Actions.

## Intégration continue

`.github/workflows/ci.yml` lance ruff puis la suite de tests à chaque push,
sur Ubuntu et Python 3.13. Le job échoue si le formatage n'est pas conforme,
si un test casse, ou si le rappel du modèle livré passe sous 0.75.

## Déploiement

L'image Docker est prête :

```powershell
docker build -t attrition-api .
docker run -p 8000:8000 -e PORT=8000 -e API_KEY=... -e DATABASE_URL=... attrition-api
```

Elle part de `python:3.13-slim`, tourne sous un utilisateur non privilégié et
lit son port dans `PORT`, ce qu'attendent la plupart des hébergeurs.

L'image a été construite et vérifiée en local : `/health` répond, `/predict`
renvoie une prédiction et la trace arrive bien en base.

La plateforme d'hébergement n'est pas encore arrêtée — voir
[`docs/avancement.md`](docs/avancement.md).

## Commandes disponibles

| Commande | Ce qu'elle fait |
|---|---|
| `attrition-api` | démarre l'API |
| `attrition-entrainer` | entraîne le modèle et écrit les métriques |
| `attrition-creer-base` | crée la base et charge les CSV |
| `attrition-creer-utilisateur` | crée un compte d'accès à l'API |
| `attrition-scorer` | prédit sur tous les employés de la base |
| `attrition-requetes` | exécute les requêtes d'analyse sur la base |

Elles sont déclarées dans `pyproject.toml` et installées avec le paquet.

## Organisation du dépôt

```
src/          le service : contrat de données, pipeline, sécurité, API
scripts/      les commandes hors service : création de base, entraînement
tests/        51 tests, un fichier par module testé
data/         les trois extraits CSV fournis
models/       le modèle entraîné et ses métriques
sql/          le schéma de la base
docs/         la documentation et le journal de bord
```

## Documentation

| Fichier | Contenu |
|---|---|
| [`docs/api.md`](docs/api.md) | routes, champs attendus, codes d'erreur |
| [`docs/modele.md`](docs/modele.md) | données, pipeline, mesures, limites |
| [`docs/features.md`](docs/features.md) | le contrat de données en détail |
| [`docs/base_de_donnees.md`](docs/base_de_donnees.md) | schéma PostgreSQL |
| [`docs/avancement.md`](docs/avancement.md) | journal de bord du projet |
