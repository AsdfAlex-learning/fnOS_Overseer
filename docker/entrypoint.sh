#!/bin/bash
set -e

# Create necessary directories if they don't exist
mkdir -p logs data/reports

# Wait for dependencies if needed (e.g., database)
# Currently not required as fnOS_Overseer doesn't use external databases

echo "Starting fnOS_Overseer..."
exec python -u web/backend/main.py
