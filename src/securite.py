"""Authentification par cle d'API."""

import os
import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

# auto_error=False : on renvoie nous-memes le 401, avec notre message.
entete_cle = APIKeyHeader(name="X-API-Key", auto_error=False)


def verifier_cle(cle: str = Security(entete_cle)):
    """Refuse la requete si l'en-tete X-API-Key ne correspond pas."""
    attendue = os.environ.get("API_KEY")
    if not attendue:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "API_KEY absente de la configuration du serveur",
        )
    # compare_digest et pas == : le temps de comparaison ne depend pas
    # du nombre de caracteres justes, donc la cle ne se devine pas.
    if not cle or not secrets.compare_digest(cle, attendue):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Cle d'API absente ou invalide"
        )
