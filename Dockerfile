FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY backend/pyproject.toml backend/uv.lock backend/requirements.txt ./

RUN uv pip install --system -r requirements.txt

COPY backend/README.md backend/alembic.ini ./
COPY backend/alembic/ ./alembic/
COPY backend/app/ ./app/
COPY backend/scripts/ ./scripts/
COPY backend/start.sh ./start.sh

RUN uv pip install --system --no-deps -e .

RUN chmod +x ./start.sh

EXPOSE 8000

CMD ["./start.sh"]
