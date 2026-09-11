"""Authentification : comptes utilisateurs, jetons JWT, cle de service."""

import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from src.database import chercher_utilisateur

ALGORITHME = "HS256"
DUREE_JETON = timedelta(minutes=30)

# Hachage d'une valeur aleatoire, compare quand le compte n'existe pas : sans
# lui, une reponse immediate revelerait que l'identifiant est inconnu.
HACHAGE_LEURRE = "$2b$12$ZfusOAoHzCnJcDwk.Zkzk.SkTPFP3728sLlINrdZuMXRYTkViCx2m"

entete_cle = APIKeyHeader(name="X-API-Key", auto_error=False)
jeton_porteur = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    """bcrypt sale lui-meme : le meme mot de passe donne deux hachages differents."""
    return bcrypt.hashpw(mot_de_passe.encode(), bcrypt.gensalt()).decode()


def verifier_mot_de_passe(mot_de_passe: str, hache: str) -> bool:
    """Rehache le candidat avec le sel du stocke, puis compare."""
    return bcrypt.checkpw(mot_de_passe.encode(), hache.encode())


def _secret_jwt() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "JWT_SECRET absent de la configuration du serveur",
        )
    return secret


def creer_jeton(identifiant: str) -> str:
    """Jeton signe, valable une demi-heure."""
    charge = {"sub": identifiant, "exp": datetime.now(timezone.utc) + DUREE_JETON}
    return jwt.encode(charge, _secret_jwt(), algorithm=ALGORITHME)


def lire_jeton(jeton: str) -> str:
    """Verifie la signature et la peremption, puis rend l'identifiant."""
    try:
        charge = jwt.decode(jeton, _secret_jwt(), algorithms=[ALGORITHME])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton invalide ou expire")
    return charge["sub"]


def authentifier(session: Session, identifiant: str, mot_de_passe: str) -> str:
    """Verifie un couple identifiant / mot de passe contre la base."""
    utilisateur = chercher_utilisateur(session, identifiant)
    hache = utilisateur.mot_de_passe_hache if utilisateur else HACHAGE_LEURRE
    correspond = verifier_mot_de_passe(mot_de_passe, hache)
    # Un seul message pour les trois cas : un compte inconnu, un mot de passe
    # faux et un compte desactive ne doivent pas se distinguer de l'exterieur.
    if not utilisateur or not correspond or not utilisateur.actif:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Identifiant ou mot de passe incorrect"
        )
    return utilisateur.identifiant


def identifier_appelant(
    cle: str = Security(entete_cle), jeton: str = Security(jeton_porteur)
) -> str:
    """Accepte un jeton d'utilisateur ou la cle de service, et dit qui appelle.

    Le nom rendu part dans la colonne appelant de predictions.
    """
    if jeton:
        return lire_jeton(jeton)

    if cle:
        attendue = os.environ.get("API_KEY")
        if not attendue:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "API_KEY absente de la configuration du serveur",
            )
        # compare_digest et pas == : le temps de comparaison ne depend pas
        # du nombre de caracteres justes, donc la cle ne se devine pas.
        if secrets.compare_digest(cle, attendue):
            return "service"

    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Authentification requise : jeton d'acces ou cle d'API",
    )
