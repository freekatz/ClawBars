FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cache layer - deps only from pyproject.toml)
COPY pyproject.toml ./
RUN python -c "import tomllib; \
    deps = tomllib.load(open('pyproject.toml','rb')).get('project',{}).get('dependencies',[]); \
    print('\n'.join(deps))" > /tmp/requirements.txt && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Copy application code and install package
COPY . .
RUN pip install --no-cache-dir --no-deps .

# Create data directories
RUN mkdir -p /app/data /app/logs

EXPOSE 8000


# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Start application: run migrations then start uvicorn
CMD ["sh", "-c", "alembic upgrade head 2>/dev/null || echo 'Alembic migration skipped (no versions or DB not ready)'; uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-1}"]
