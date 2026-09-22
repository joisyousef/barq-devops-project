# #!/usr/bin/env bash
# set -euo pipefail
# echo 'NOT IMPLEMENTED: write the PostgreSQL backup script.' >&2
# exit 2
#!/usr/bin/env bash
set -euo pipefail

mkdir -p backups

FILE="backups/barq_tasks_$(date -u +%Y%m%dT%H%M%SZ).dump"

docker exec postgres pg_dump \
    -U barq_app \
    -d barq_tasks \
    -Fc \
    > "$FILE"

echo "Backup created: $FILE"
