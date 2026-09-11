---
title: API attrition TechNova
emoji: 📉
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# API de prédiction du risque de démission

Expose le modèle d'attrition de TechNova Partners derrière une API REST.
Documentation interactive sur `/docs`, état du service sur `/health`.

L'en-tête YAML ci-dessus configure le Space Hugging Face ; le reste de cette
documentation arrive à l'étape 8.

## Installation

```bash
pip install -e ".[dev]"
```

## Utilisation

```bash
attrition-api
```

Deux variables d'environnement sont attendues, décrites dans `.env.example` :
`DATABASE_URL` pour la traçabilité des prédictions, `API_KEY` pour l'accès à
`/predict`.

## Tests

```bash
pytest
```
