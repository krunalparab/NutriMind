#!/bin/bash
# start.sh — NutriMind Railway startup script
# Downloads data files to /app (absolute) then starts gunicorn

PARQUET_URL="https://media.githubusercontent.com/media/krunalparab/NutriMind/master/recipes.parquet"
DB_URL="https://media.githubusercontent.com/media/krunalparab/NutriMind/master/instructions.db"

# ── Download recipes.parquet SYNCHRONOUSLY (40 MB, ~5 seconds) ───────────────
# Required before first API call — lazy-loaded by main.py
if [ ! -f "/app/recipes.parquet" ]; then
    echo "[startup] Downloading recipes.parquet (40 MB)..." 
    curl -L "$PARQUET_URL" -o /app/recipes.parquet
    echo "[startup] recipes.parquet ready ($(du -sh /app/recipes.parquet | cut -f1))"
else
    echo "[startup] recipes.parquet already present ($(du -sh /app/recipes.parquet | cut -f1))"
fi

# ── Download instructions.db IN BACKGROUND (340 MB, ~60 seconds) ─────────────
# API returns recipes with empty instructions until this completes (handled gracefully)
if [ ! -f "/app/instructions.db" ]; then
    echo "[startup] Downloading instructions.db (340 MB) in background..."
    curl -L "$DB_URL" -o /app/instructions.db.tmp && mv /app/instructions.db.tmp /app/instructions.db && echo "[startup] instructions.db ready" &
else
    echo "[startup] instructions.db already present ($(du -sh /app/instructions.db | cut -f1))"
fi

# ── Start gunicorn (NO --preload: port opens immediately, health-check passes) ─
exec gunicorn --chdir app "app:create_app()" \
    --bind "0.0.0.0:${PORT:-8080}" \
    --workers 1 \
    --timeout 120
