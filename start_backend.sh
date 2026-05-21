#!/usr/bin/env bash
# Start the FastAPI backend
cd "$(dirname "$0")"
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
