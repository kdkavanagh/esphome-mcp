FROM python:3.13-slim

WORKDIR /app

ARG SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0

COPY pyproject.toml .
COPY src/ src/

RUN pip install uv && \
    SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION} uv pip install --system --no-cache .

EXPOSE 8080

ENTRYPOINT ["esphome-mcp-web"]
