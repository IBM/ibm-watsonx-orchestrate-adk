# Create wxo_observability database if it doesn't exist
if psql -U $PG_USER -lqt | cut -d '|' -f 1 | grep -qw wxo_observability; then
    echo 'Existing wxo_observability DB found'
else
    echo 'Creating wxo_observability DB'
    createdb -U $PG_USER -O $PG_USER wxo_observability;
    psql -U $PG_USER -q -d postgres -c "GRANT CONNECT ON DATABASE wxo_observability TO $PG_USER";
fi

# Run observability-specific migrations
OBSERVABILITY_MIGRATIONS_FILE="/var/lib/postgresql/applied_migrations/observability_migrations.txt"
touch "$OBSERVABILITY_MIGRATIONS_FILE"

for file in /docker-entrypoint-initdb.d/observability/*.sql; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        
        if grep -Fxq "$filename" "$OBSERVABILITY_MIGRATIONS_FILE"; then
            echo "Skipping already applied observability migration: $filename"
        else
            echo "Applying observability migration: $filename"
            if psql -U $PG_USER -d wxo_observability -q -f "$file" > /dev/null 2>&1; then
                echo "$filename" >> "$OBSERVABILITY_MIGRATIONS_FILE"
            else
                echo "Error applying observability migration: $filename. Stopping migrations."
                exit 1
            fi
        fi
    fi
done