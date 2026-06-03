FROM python:3.12-slim AS base

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ src/
COPY data/ data/
COPY migrations/ migrations/
COPY alembic.ini ./

# Create storage directory
RUN mkdir -p /app/storage/artifacts

EXPOSE 8000

# Run with uvicorn
CMD ["uv", "run", "uvicorn", "pwps_agent_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
