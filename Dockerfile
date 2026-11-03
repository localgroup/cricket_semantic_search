FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    MONGODB_URI=mongodb://127.0.0.1:27017 \
    QDRANT_URL=http://127.0.0.1:6333 \
    MONGODB_DATABASE=cricket_rag \
    MONGODB_COLLECTION=cricket_events \
    QDRANT_COLLECTION=cricket_events \
    OUTPUT_DIR=/app/output \
    INPUT_FILE=/app/data/cricket_log.txt

WORKDIR /app
ARG MONGO_VERSION=7.0.16
ARG QDRANT_VERSION=1.12.4

# This single image intentionally contains the app, MongoDB and Qdrant.
# MongoDB/Qdrant are pinned for repeatable local development.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl supervisor tini build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /opt/mongodb /opt/qdrant /var/lib/mongodb /qdrant/storage /var/log/supervisor \
    && curl -fsSL "https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-debian12-${MONGO_VERSION}.tgz" -o /tmp/mongodb.tgz \
    && tar -xzf /tmp/mongodb.tgz --strip-components=2 -C /opt/mongodb "mongodb-linux-x86_64-debian12-${MONGO_VERSION}/bin/mongod" \
    && rm /tmp/mongodb.tgz \
    && curl -fsSL "https://github.com/qdrant/qdrant/releases/download/v${QDRANT_VERSION}/qdrant-x86_64-unknown-linux-gnu.tar.gz" -o /tmp/qdrant.tgz \
    && tar -xzf /tmp/qdrant.tgz -C /opt/qdrant \
    && rm /tmp/qdrant.tgz \
    && chmod +x /opt/mongodb/mongod /opt/qdrant/qdrant

COPY backend/requirements.txt /app/requirements.txt
COPY backend/constraints.txt /app/constraints.txt

# Install CPU-only PyTorch and constrain dependency resolution.
RUN pip install --upgrade pip \
    && pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        "torch==2.14.1+cpu" \
    && pip install --no-cache-dir \
        -c /app/constraints.txt \
        -r /app/requirements.txt \
    && pip check
COPY backend/ /app/
COPY data/ /app/data/
COPY mcp_server/ /app/mcp_server/
COPY docker/supervisord.conf /etc/supervisor/conf.d/cricket-app.conf
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh \
    && mkdir -p /app/output /app/.cache/huggingface /var/lib/mongodb /qdrant/storage \
    && touch /app/output/.gitkeep

EXPOSE 8000 27017 6333 6334 8050
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]
