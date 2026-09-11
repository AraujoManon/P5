"""Cree un compte d'acces a l'API, ou change son mot de passe.

Lancement :
    attrition-creer-utilisateur martine
"""

import sys
from getpass import getpass

from sqlalchemy import text

from src.database import fabrique_session
from src.securite import hacher_mot_de_passe

ENREGISTREMENT = text(
    "INSERT INTO utilisateurs (identifiant, mot_de_passe_hache) "
    "VALUES (:identifiant, :hache) "
    "ON CONFLICT (identifiant) DO UPDATE SET mot_de_passe_hache = :hache"
)

LONGUEUR_MINIMALE = 12


def main():
    if len(sys.argv) != 2:
        print("Usage : attrition-creer-utilisateur <identifiant>")
        raise SystemExit(1)

    identifiant = sys.argv[1]

    # getpass et pas input : le mot de passe ne s'affiche pas et ne part pas
    # dans l'historique du terminal.
    mot_de_passe = getpass("Mot de passe : ")
    if len(mot_de_passe) < LONGUEUR_MINIMALE:
        print(f"Trop court : {LONGUEUR_MINIMALE} caracteres minimum.")
        raise SystemExit(1)
    if mot_de_passe != getpass("Confirmation : "):
        print("Les deux saisies different.")
        raise SystemExit(1)

    with fabrique_session()() as session:
        session.execute(
            ENREGISTREMENT,
            {"identifiant": identifiant, "hache": hacher_mot_de_passe(mot_de_passe)},
        )
        session.commit()

    print(f"Compte {identifiant} enregistre.")


if __name__ == "__main__":
    main()
