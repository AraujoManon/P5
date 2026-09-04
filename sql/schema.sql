-- Base attrition. Noms de colonnes repris des CSV, fautes comprises.

-- Ordre inverse des CREATE, a cause des cles etrangeres.
DROP TABLE IF EXISTS predictions;
DROP TABLE IF EXISTS employes_eval;
DROP TABLE IF EXISTS employes_sondage;
DROP TABLE IF EXISTS employes_sirh;


CREATE TABLE employes_sirh (
    id_employee                    integer PRIMARY KEY,
    age                            integer NOT NULL,
    genre                          text    NOT NULL,
    revenu_mensuel                 integer NOT NULL,
    statut_marital                 text    NOT NULL,
    departement                    text    NOT NULL,
    poste                          text    NOT NULL,
    nombre_experiences_precedentes integer NOT NULL,
    nombre_heures_travailless      integer NOT NULL,
    annee_experience_totale        integer NOT NULL,
    annees_dans_l_entreprise       integer NOT NULL,
    annees_dans_le_poste_actuel    integer NOT NULL
);


CREATE TABLE employes_sondage (
    code_sondage                        integer PRIMARY KEY
        REFERENCES employes_sirh (id_employee),
    a_quitte_l_entreprise               text    NOT NULL,
    nombre_participation_pee            integer NOT NULL,
    nb_formations_suivies               integer NOT NULL,
    nombre_employee_sous_responsabilite integer NOT NULL,
    distance_domicile_travail           integer NOT NULL,
    niveau_education                    integer NOT NULL,
    domaine_etude                       text    NOT NULL,
    ayant_enfants                       text    NOT NULL,
    frequence_deplacement               text    NOT NULL,
    annees_depuis_la_derniere_promotion integer NOT NULL,
    annes_sous_responsable_actuel       integer NOT NULL
);


-- eval_number vaut "E_" + id_employee.
CREATE TABLE employes_eval (
    eval_number                               text    PRIMARY KEY,
    id_employee                               integer NOT NULL UNIQUE
        REFERENCES employes_sirh (id_employee),
    satisfaction_employee_environnement       integer NOT NULL,
    satisfaction_employee_nature_travail      integer NOT NULL,
    satisfaction_employee_equipe              integer NOT NULL,
    satisfaction_employee_equilibre_pro_perso integer NOT NULL,
    note_evaluation_precedente                integer NOT NULL,
    note_evaluation_actuelle                  integer NOT NULL,
    niveau_hierarchique_poste                 integer NOT NULL,
    heure_supplementaires                     text    NOT NULL,
    -- pourcentage stocke en texte dans le CSV, nettoye a l'insertion
    augementation_salaire_precedente          numeric(5, 2) NOT NULL
);


CREATE TABLE predictions (
    id             bigserial PRIMARY KEY,
    horodatage     timestamptz   NOT NULL DEFAULT now(),
    entree         jsonb         NOT NULL,
    probabilite    numeric(5, 4) NOT NULL CHECK (probabilite BETWEEN 0 AND 1),
    prediction     text          NOT NULL CHECK (prediction IN ('Oui', 'Non')),
    seuil_applique numeric(3, 2) NOT NULL,
    version_modele text          NOT NULL
);

CREATE INDEX idx_predictions_horodatage ON predictions (horodatage DESC);
