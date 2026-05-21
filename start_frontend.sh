#!/usr/bin/env bash
# Start the Streamlit frontend
cd "$(dirname "$0")"
streamlit run frontend/app.py --server.port 8501
