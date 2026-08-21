# `src/features.py` — le contrat de données

## À quoi ça sert

Le modèle de machine learning ne sait manipuler que des nombres. Il ne sait pas
lire `"Occasionnel"`, ni `"11 %"`, et il ne sait pas calculer tout seul qu'un
salarié a passé 75 % de sa carrière dans l'entreprise.

Ce fichier fait deux choses :

1. il **déclare** ce que le modèle attend — quelles colonnes, quels types,
   quelles valeurs sont autorisées ;
2. il **transforme** une ligne brute en ligne que le modèle peut manger.

Il ne contient aucune logique métier compliquée. C'est un fichier de référence
que tout le reste du projet importe.

## Exemple concret

Un employé arrive avec ses 26 champs. Voici un extrait avant transformation :

```
age                                    41
revenu_mensuel                         5993
annees_dans_l_entreprise               6
annee_experience_totale                8
annees_dans_le_poste_actuel            4
annees_depuis_la_derniere_promotion    0
frequence_deplacement                  "Occasionnel"
augementation_salaire_precedente       "11 %"
satisfaction_employee_environnement    2
satisfaction_employee_nature_travail   4
satisfaction_employee_equipe           1
satisfaction_employee_equilibre        1
```

Après passage dans `preparer_donnees()` :

```
frequence_deplacement            1        <- "Occasionnel" traduit en chiffre
augementation_salaire_precedente 11       <- "11 %" nettoyé

ratio_fidelite                   0.75     <- 6 / 8
ratio_stagnation_poste           0.67     <- 4 / 6
ratio_attente_promotion          0.0      <- 0 / 6
revenu_par_annee_experience      749.12   <- 5993 / 8
satisfaction_moyenne             2.0      <- (2 + 4 + 1 + 1) / 4
```

On passe de 26 colonnes à 31 : les 26 d'origine, plus les 5 variables calculées.

## Ce que contient le fichier

### Les déclarations

| Constante | Contenu |
|---|---|
| `COLONNE_CIBLE` | le nom de la variable à prédire |
| `MAPPING_CIBLE` | `Oui` → 1, `Non` → 0 |
| `COLONNES_ECARTEES` | les 7 colonnes des CSV qu'on n'utilise pas, avec la raison |
| `COLONNES_ENTIERES` | les 12 champs numériques classiques |
| `COLONNES_ECHELLE` | les 7 notes de 1 à 4 ou 1 à 5 |
| `COLONNE_ORDINALE` | `frequence_deplacement` |
| `COLONNES_NOMINALES` | les 6 champs texte sans ordre |
| `COLONNES_ENTREE` | l'assemblage des 4 précédentes = **26 colonnes** |
| `BORNES` | le min et le max de chaque champ numérique |
| `MODALITES` | les valeurs autorisées de chaque champ texte |
| `ORDRE_DEPLACEMENT` | `Aucun`=0, `Occasionnel`=1, `Frequent`=2 |
| `AXES_SATISFACTION` | les 4 axes du sondage à moyenner |
| `FEATURES_METIER` | les noms des 5 variables calculées |

### Les fonctions

| Fonction | Ce qu'elle fait |
|---|---|
| `nettoyer_pourcentage()` | `"11 %"` → `11` |
| `encoder_frequence_deplacement()` | `"Occasionnel"` → `1` |
| `creer_features_metier()` | calcule les 5 ratios |
| `preparer_donnees()` | enchaîne les trois précédentes |

## Pourquoi les colonnes sont rangées en 4 groupes

Ce n'est pas du rangement décoratif : chaque groupe recevra un traitement
différent dans le pipeline scikit-learn.

| Groupe | Traitement |
|---|---|
| Entiers | mise à l'échelle |
| Échelles 1–4 | rien — déjà numériques et déjà ordonnées |
| Ordinale | encodée 0 / 1 / 2 pour garder l'ordre |
| Nominales | One Hot Encoding |

`frequence_deplacement` mérite une explication. Ses trois valeurs ont un ordre
naturel : `Aucun` < `Occasionnel` < `Frequent`. Un One Hot Encoding créerait
trois colonnes indépendantes et détruirait cette information. On l'encode donc
en 0, 1, 2.

À l'inverse, il n'y a aucun ordre entre `Consultant` et `Manager` : les encoder
en 0 et 1 ferait croire au modèle que l'un est « plus grand » que l'autre. D'où
le One Hot pour les nominales.

## Pourquoi les bornes sont plus larges que les données

Dans le jeu d'entraînement, `age` va de 18 à 60. On autorise pourtant 18 à 60
en validation, et `nombre_experiences_precedentes` accepte jusqu'à 20 alors
qu'on n'observe que 0 à 9.

La raison : une API doit accepter toute valeur métier plausible. Refuser un
salarié parce qu'aucun de son profil n'était dans le jeu d'entraînement serait
incompréhensible pour l'utilisateur RH.

Cas particulier : `note_evaluation_actuelle` ne contient que des 3 et des 4 dans
les données. On accepte quand même 1 à 4, qui est l'échelle métier réelle. C'est
une limite connue du modèle : il n'a jamais vu de 1 ni de 2 sur ce champ.

## Pourquoi ce fichier est séparé du reste

Le même code de préparation tourne à deux moments très éloignés :

- à l'**entraînement**, sur les 1470 lignes du CSV ;
- dans l'**API**, sur une seule ligne, des mois plus tard.

Si ces calculs étaient écrits deux fois — une version dans le script
d'entraînement, une version dans l'API — les deux finiraient par diverger. On
corrige une formule d'un côté, on oublie l'autre.

Le problème, c'est que rien ne préviendrait. L'API recevrait bien 31 nombres,
juste pas les bons. La prédiction serait fausse, sans aucune erreur affichée.

Un seul fichier, importé des deux côtés, élimine ce risque. C'est aussi ce que
`preparer_donnees()` garantit en fonctionnant à l'identique sur 1470 lignes et
sur une seule.

## Les 7 colonnes écartées

| Colonne | Raison |
|---|---|
| `id_employee` | identifiant, aucun pouvoir prédictif |
| `code_sondage` | strictement égal à `id_employee` sur les 1470 lignes |
| `eval_number` | identifiant technique de l'évaluation |
| `nombre_heures_travailless` | vaut 80 pour tout le monde |
| `nombre_employee_sous_responsabilite` | vaut 1 pour tout le monde |
| `ayant_enfants` | vaut `Y` pour tout le monde |
| `niveau_hierarchique_poste` | choix issu de l'analyse P4 |

Une colonne où tout le monde a la même valeur ne distingue personne : elle ne
peut rien expliquer.

Les identifiants sont pires que inutiles. Le modèle apprendrait « l'employé 47
est parti » au lieu de « les gens qui font beaucoup d'heures supplémentaires
partent ». Et le jour où l'API reçoit l'employé 2000, cet identifiant ne lui dit
rien du tout.
