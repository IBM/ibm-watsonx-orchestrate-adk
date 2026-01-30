# Create mcpgateway database if it doesn't exist
if psql -U $PG_USER -lqt | cut -d '|' -f 1 | grep -qw mcpgateway; then
    echo 'Existing mcpgateway DB found'
else
    echo 'Creating mcpgateway DB'
    createdb -U $PG_USER -O $PG_USER mcpgateway;
    psql -U $PG_USER -q -d postgres -c "GRANT CONNECT ON DATABASE mcpgateway TO $PG_USER";
fi