echo 'Waiting for pg to initialize...'

timeout=$PG_TIMEOUT
while [[ -z `pg_isready | grep 'accepting connections'` ]] && (( timeout > 0 )); do
  ((timeout-=1)) && sleep 1;
done

if psql -U $PG_USER -lqt | cut -d \| -f 1 | grep -qw langflow; then
  echo 'Existing Langflow DB found'
else
  echo 'Creating Langflow DB'
  createdb -U $PG_USER -O $PG_USER langflow;
  psql -U $PG_USER -q -d postgres -c "GRANT CONNECT ON DATABASE langflow TO $PG_USER";
fi