# Create architect database if it doesn't exist
if psql -U $PG_USER -lqt | cut -d \| -f 1 | grep -qw architect; then
    echo 'Existing architect DB found'
else
    echo 'Creating architect DB'
    createdb -U $PG_USER -O $PG_USER architect;
    psql -U $PG_USER -q -d postgres -c "GRANT CONNECT ON DATABASE architect TO $PG_USER";
fi

# Run architect-specific migrations
ARCHITECT_MIGRATIONS_FILE="/var/lib/postgresql/applied_migrations/architect_migrations.txt"
touch "$ARCHITECT_MIGRATIONS_FILE"

for file in /docker-entrypoint-initdb.d/agent_architecture/migrations/*.sql; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        
        if grep -Fxq "$filename" "$ARCHITECT_MIGRATIONS_FILE"; then
            echo "Skipping already applied architect migration: $filename"
        else
            echo "Applying architect migration: $filename"
            if psql -U $PG_USER -d architect -q -f "$file" > /dev/null 2>&1; then
                echo "$filename" >> "$ARCHITECT_MIGRATIONS_FILE"
            else
                echo "Error applying architect migration: $filename. Stopping migrations."
                exit 1
            fi
        fi
    fi
done