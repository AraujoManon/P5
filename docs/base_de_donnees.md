# Base de données

PostgreSQL 17, base `attrition`. Quatre tables : trois pour le jeu de données,
une pour tracer les appels au modèle.

## Schéma

```mermaid
erDiagram
    employes_sirh ||--|| employes_sondage : "id_employee = code_sondage"
    employes_sirh ||--|| employes_eval : "id_employee"

    employes_sirh {
        integer id_employee PK
        integer age
        text    genre
        integer revenu_mensuel
        text    statut_marital
        text    departement
        text    poste
        integer nombre_experiences_precedentes
        integer nombre_heures_travailless
        integer annee_experience_totale
        integer annees_dans_l_entreprise
        integer annees_dans_le_poste_actuel
    }

    employes_sondage {
        integer code_sondage PK-FK
        text    a_quitte_l_entreprise
        integer nombre_participation_pee
        integer nb_formations_suivies
        integer nombre_employee_sous_responsabilite
        integer distance_domicile_travail
        integer niveau_education
        text    domaine_etude
        text    ayant_enfants
        text    frequence_deplacement
        integer annees_depuis_la_derniere_promotion
        integer annes_sous_responsable_actuel
    }

    employes_eval {
        text    eval_number PK
        integer id_employee FK
        integer satisfaction_employee_environnement
        integer satisfaction_employee_nature_travail
        integer satisfaction_employee_equipe
        integer satisfaction_employee_equilibre_pro_perso
        integer note_evaluation_precedente
        integer note_evaluation_actuelle
        integer niveau_hierarchique_poste
        text    heure_supplementaires
        numeric augementation_salaire_precedente
    }

    predictions {
        bigserial   id PK
        timestamptz horodatage
        jsonb       entree
        numeric     probabilite
        text        prediction
        numeric     seuil_applique
        text        version_modele
    }
```

`predictions` n'a pas de clé étrangère vers `employes_sirh` : l'API répond sur
des employés qui ne sont pas forcément en base, y compris un candidat ou un
profil hypothétique saisi par les RH.

## Choix de modélisation

### Trois tables plutôt qu'une

Les données viennent de trois extraits
distincts — SIRH, sondage interne, évaluations annuelles. Les recoller en une
table large aurait effacé cette origine. Chaque table garde la clé primaire de
son système source.

### `eval_number` en texte

Le système d'évaluation numérote `E_1`, `E_2`,
`E_4`. C'est `"E_" + id_employee`, vérifié sur les 1470 lignes. La table garde
l'identifiant tel qu'il arrive et porte en plus `id_employee`, qui supporte la
clé étrangère.

### Les entrées de prédiction en JSONB

Les 26 champs sont déjà décrits une
fois dans `src/schemas.py`. Les redéclarer en colonnes SQL ferait deux endroits
à modifier à chaque évolution du contrat. Le JSONB reste interrogeable :

```sql
SELECT entree->>'poste', avg(probabilite)
FROM predictions
GROUP BY 1;
```

### `augementation_salaire_precedente` en `numeric`

Le CSV contient `"11 %"`.
La valeur est nettoyée à l'insertion : un pourcentage est un nombre, et toute
requête qui en fait une moyenne devrait sinon le renettoyer.

### Pas de `CHECK` sur les colonnes catégorielles

Les modalités autorisées vivent dans `src/schemas.py`. En revanche `predictions`
en a deux, sur `probabilite` et `prediction` : ce sont des sorties du code, et
une valeur aberrante y signalerait un bug à corriger tout de suite.

## Scripts

| Script | Rôle |
|---|---|
| `sql/schema.sql` | définition des quatre tables |
| `scripts/create_db.py` | crée la base, rejoue le schéma, insère les 3 CSV |
| `scripts/requetes.py` | requêtes d'analyse et suivi des prédictions |
| `scripts/scorer_base.py` | fait tourner le modèle sur les 1470 employés |

Le schéma est rejouable : `create_db.py` supprime et recrée les tables à chaque
exécution.

## Mise en route

```powershell
Copy-Item .env.example .env   # puis renseigner le mot de passe
python -m scripts.create_db
python -m scripts.requetes
```
