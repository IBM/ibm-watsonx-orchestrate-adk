APPLIED_MIGRATIONS_FILE="/var/lib/postgresql/applied_migrations/applied_migrations.txt"
mkdir -p "$(dirname "$APPLIED_MIGRATIONS_FILE")"
touch "$APPLIED_MIGRATIONS_FILE"

for file in /docker-entrypoint-initdb.d/*.sql; do
    filename=$(basename "$file")
    if grep -Fxq "$filename" "$APPLIED_MIGRATIONS_FILE"; then
        echo "Skipping already applied migration: $filename"
    else
        echo "Applying migration: $filename"
        if psql -U $PG_USER -d postgres -q -f "$file" > /dev/null 2>&1; then
            echo "$filename" >> "$APPLIED_MIGRATIONS_FILE"
        else
            echo "Error applying $filename. Stopping migrations."
            exit 1
        fi
    fi
done