# Version Python correspondant à votre environnement local (.venv)
FROM python:3.12-slim-bookworm

# Installer les dépendances système pour Playwright/Chromium
RUN apt-get update && \
    apt-get install -y \
    curl \
    gnupg \
    git \
    gcc \
    g++ \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    libwayland-client0 \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Installer Poetry
ENV POETRY_VERSION=1.8.2
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Configurer Poetry
RUN poetry config virtualenvs.in-project true

# Copier les fichiers nécessaires
WORKDIR /app
COPY pyproject.toml poetry.lock ./
# Copier le code source
COPY src /app/src

# Installer les dépendances Python (y compris Playwright)
RUN poetry install

# Installer Chromium via Playwright
RUN poetry run playwright install chromium
RUN poetry run playwright install-deps


# Exposer le port et lancer l'application
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "src.kpi_api.main:app", "--host", "0.0.0.0", "--port", "8000"]