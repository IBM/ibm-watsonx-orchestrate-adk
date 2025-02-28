Generate cert:

```bash
openssl req -nodes -new -x509 -days 3650 \
    -keyout server.key \
    -out server.cert \
    -subj "/CN=tempus" \
    -extensions san \
    -config <(
        cat <<-EOF
        [req]
        distinguished_name=req
        [san]
        subjectAltName=@alt_names
        [alt_names]
        DNS.1=localhost
        DNS.2=atm
        DNS.2=mape
EOF
    )
```