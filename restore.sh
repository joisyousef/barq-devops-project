# #!/usr/bin/env bash
# set -euo pipefail
# echo 'NOT IMPLEMENTED: write the PostgreSQL restore script and prove recovery.' >&2
# exit 2
#!/usr/bin/env bash
set -euo pipefail

BACKUP="${1:?Usage: ./restore.sh backups/file.dump}"

RESTORE_DB="barq_restore_test"

docker exec postgres dropdb \
    -U barq_app \
    --if-exists \
    "$RESTORE_DB"

docker exec postgres createdb \
    -U barq_app \
    "$RESTORE_DB"

cat "$BACKUP" | docker exec -i postgres pg_restore \
    -U barq_app \
    -d "$RESTORE_DB" \
    --no-owner

echo "Restore completed into database: $RESTORE_DB"

docker exec postgres psql \
    -U barq_app \
    -d "$RESTORE_DB" \
    -c "SELECT COUNT(*) FROM records; SELECT id, title FROM records ORDER BY id DESC LIMIT 3;"

docker exec postgres dropdb \
    -U barq_app \
    "$RESTORE_DB"

echo "Restore verification completed."
