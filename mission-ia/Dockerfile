# L'assistant du portail, livré en conteneur.
#
#   docker build -t mission-ia .
#   docker run -p 8000:8000 mission-ia          # Ollama tourne sur l'hôte
#
# Les versions exactes viennent de uv.lock (--frozen) : l'image construite
# demain est celle d'aujourd'hui. Le service tourne sous un utilisateur sans
# droits, et joint l'Ollama de l'hôte (host.docker.internal) : le modèle ne
# vit pas dans l'image.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.27 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Les dépendances d'abord : cette couche ne se reconstruit que si uv.lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY jobportal ./jobportal
RUN uv sync --frozen --no-dev

RUN useradd --create-home assistant
USER assistant
ENV PATH="/app/.venv/bin:$PATH" OLLAMA_HOST=http://host.docker.internal:11434
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/sante')"
CMD ["uvicorn", "jobportal.api:app", "--host", "0.0.0.0", "--port", "8000"]
