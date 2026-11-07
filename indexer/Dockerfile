FROM python:3.12.12-slim-bookworm AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY indexer/requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install -r requirements.txt

FROM python:3.12.12-slim-bookworm AS runtime
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    HOME=/tmp TMPDIR=/tmp ANONYMIZED_TELEMETRY=False
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends tesseract-ocr poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 rahbar && useradd --uid 10001 --gid 10001 --no-create-home rahbar
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=10001:10001 indexer/pipeline ./pipeline
COPY --chown=10001:10001 indexer/entrypoint.py ./entrypoint.py
COPY --chown=10001:10001 eval/fixtures /fixtures
USER 10001:10001
CMD ["python", "entrypoint.py"]
