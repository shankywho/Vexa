FROM python:3.12-slim

# Prevent Python from writing .pyc files & enable unbuffered stdout
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first
COPY pyproject.toml uv.lock requirements.txt ./

# Install dependencies into system environment using uv
RUN uv pip install --system -r requirements.txt

# Copy application code, migrations, and assets
COPY README.md alembic.ini ./
COPY alembic/ ./alembic/
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY start.sh ./start.sh

# Install the local project package without reinstalling dependencies
RUN uv pip install --system --no-deps -e .

RUN chmod +x ./start.sh

EXPOSE 8000

CMD ["./start.sh"]
