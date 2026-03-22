FROM python:3.13-slim

WORKDIR /app

ARG SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0

COPY pyproject.toml .
COPY src/ src/

RUN pip install uv && \
    SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION} uv pip install --system --no-cache .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import httpx, os; httpx.get(os.environ['ESPHOME_DASHBOARD_URL'].rstrip('/')+'/ping', timeout=5).raise_for_status()"

ENTRYPOINT ["esphome-mcp-web"]
