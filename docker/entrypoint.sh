#!/bin/sh
set -eu
mkdir -p /var/lib/mongodb /qdrant/storage /app/output /app/.cache/huggingface
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
