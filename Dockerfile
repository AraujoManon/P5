FROM python:3.13-slim

# Hugging Face lance le conteneur avec l'utilisateur 1000, jamais root.
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /home/user/app

COPY --chown=user pyproject.toml ./
COPY --chown=user src/ src/
COPY --chown=user scripts/ scripts/
COPY --chown=user models/ models/

# Installation editable : main.py cherche le modele en remontant d'un dossier.
# Une installation classique copierait src/ dans site-packages, loin de models/.
RUN pip install --no-cache-dir -e .

ENV PORT=7860
EXPOSE 7860
CMD ["attrition-api"]
