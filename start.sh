#!/bin/bash
# Start the trade monitor (ingestion, scoring, retraining) in the background
python main.py &

# Start the API in the foreground
exec uvicorn src.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
