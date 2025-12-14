#!/bin/bash

CORES=$(nproc)
WORKERS=$((CORES * 2))

MIN_WORKERS=1
MAX_WORKERS=8
if [ $WORKERS -lt $MIN_WORKERS ]; then
    WORKERS=$MIN_WORKERS
elif [ $WORKERS -gt $MAX_WORKERS ]; then
    WORKERS=$MAX_WORKERS
fi


echo "Starting with $WORKERS workers..."

exec uvicorn app.main:app \
    --host "0.0.0.0" \
    --port 8000 \
    --workers $WORKERS \
    --log-level info \
    --timeout-keep-alive 65 \
    --limit-max-requests 10000 \
    --proxy-headers \
    --forwarded-allow-ips "*"
