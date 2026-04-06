#!/bin/bash
# Start the background worker (ingestion + ML)
python main.py &

# Start the FastAPI server
uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}