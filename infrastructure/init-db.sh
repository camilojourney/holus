#!/bin/bash
# ==============================================================================
# Holus — PostgreSQL Initialization Script
# Creates multiple databases and enables pgvector on each.
# Runs automatically on first container start via docker-entrypoint-initdb.d.
# ==============================================================================

set -euo pipefail

# The POSTGRES_USER and POSTGRES_DB are set by the Docker environment.
# This script creates ADDITIONAL databases needed by Holus services.

DATABASES=("n8n" "temporal" "temporal_visibility" "langfuse")

echo "=== Holus DB Init: Creating additional databases ==="

for db in "${DATABASES[@]}"; do
    echo "Creating database: $db"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        SELECT 'CREATE DATABASE $db OWNER $POSTGRES_USER'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
EOSQL
done

# Enable pgvector extension on all databases (including the default holus db)
ALL_DATABASES=("$POSTGRES_DB" "${DATABASES[@]}")

for db in "${ALL_DATABASES[@]}"; do
    echo "Enabling pgvector on: $db"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" <<-EOSQL
        CREATE EXTENSION IF NOT EXISTS vector;
EOSQL
done

echo "=== Holus DB Init: Complete ==="
echo "Databases created: ${ALL_DATABASES[*]}"
