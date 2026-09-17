#!/bin/bash

# AITU Gaming Hub - Startup Script

echo "Checking dependencies..."

# 1. Check PostgreSQL
if ! pg_isready -h localhost -p 5432 -U postgres >/dev/null 2>&1; then
    echo "❌ Error: PostgreSQL is not running or not accepting connections on localhost:5432."
    echo "   You can start it by running: sudo systemctl start postgresql"
    exit 1
else
    echo "✅ PostgreSQL is running."
fi

# 2. Check Redis (using nc or ping if available)
if command -v nc >/dev/null 2>&1; then
    if ! nc -z localhost 6379; then
        echo "❌ Error: Redis/Valkey is not running on localhost:6379."
        echo "   You can start it by running: sudo systemctl start redis (or sudo systemctl start valkey on Arch Linux)"
        exit 1
    else
        echo "✅ Redis is running."
    fi
else
    echo "⚠️  Netcat (nc) not found, skipping Redis port check."
fi

# 3. Activate Virtual Environment
if [ -f ".venv/bin/activate" ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
else
    echo "❌ Error: Virtual environment (.venv) not found. Please run 'python3 -m venv .venv' and install requirements."
    exit 1
fi

# 4. Run Migrations (Safe to run multiple times)
echo "🛠️  Running database migrations..."
alembic upgrade head

# 5. Start the application
echo "🚀 Starting AITU Gaming Hub..."
python main.py
