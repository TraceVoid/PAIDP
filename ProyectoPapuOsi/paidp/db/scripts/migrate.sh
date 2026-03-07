#!/bin/bash
set -e

DB_HOST=${DB_HOST:-postgres}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-paidp}
DB_USER=${DB_USER:-admin}
DB_PASSWORD=${DB_PASSWORD:-admin}

export PGPASSWORD=$DB_PASSWORD

echo "Corriendo migraciones de base de datos.."

for file in /app/db/migrations/*.sql
do
  echo "Aplicando migracion: $file"
  psql \
    -h $DB_HOST \
    -p $DB_PORT \
    -U $DB_USER \
    -d $DB_NAME \
    -f $file
done

echo "Todas las migraciones completadas exitosamente