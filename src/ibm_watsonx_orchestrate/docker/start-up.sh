set -e

check_service_ready() {
    local port=$1
    local retries=20
    local wait_time=30

    for ((i=1; i<=retries; i++)); do
        if curl --silent --fail -k https://127.0.0.1:$port/health/alive; then
            echo "[INFO] Service is ready on port $port."
            return 0
        else
            echo "[INFO] Waiting for service on port $port... Attempt $i/$retries"
            sleep $wait_time
        fi
    done

    echo "[ERROR] Service on port $port did not become ready after $((retries * wait_time)) seconds."
    return 1
}

if [ "$IS_WXO_LITE" = "TRUE" ]; then
    echo "[INFO] Lite mode detected - generating self-signed certificates into /tmp"

    mkdir -p /tmp/certs

    openssl req -x509 -nodes -days 365 \
        -newkey rsa:2048 \
        -keyout /tmp/certs/key.pem \
        -out /tmp/certs/cert.pem \
        -subj "/CN=localhost"

    echo "[INFO] Starting BOTH servers (HTTP on 4321 + HTTPS on 4322) with sequential worker startup"


    uvicorn --host 0.0.0.0 --port 4322 \
        --ssl-keyfile /tmp/certs/key.pem \
        --ssl-certfile /tmp/certs/cert.pem \
        --log-config /app/config/logs/log_conf.yaml \
        --log-level debug \
        wo_archer.api.main:app &
    echo "[INFO] Started HTTPS server. Waiting for readiness..."
    
    check_service_ready 4322

    uvicorn --host 0.0.0.0 --port 4321 \
        --log-config /app/config/logs/log_conf.yaml \
        --log-level debug \
        --workers 2 \
        wo_archer.api.main:app &
    echo "[INFO] Started HTTP worker $i. Waiting for readiness..."
    
else
    uvicorn --host 0.0.0.0 --port 4321 \
        --log-config /app/config/logs/log_conf.yaml \
        --log-level debug \
        wo_archer.api.main:app &
    echo "[INFO] Started HTTP worker $i. Waiting for readiness..."    
fi

wait
