# Nginx — single entry point

Nginx is the only service of the application that publishes ports on the host:

| Port | What it does |
|------|--------------|
| 443 | HTTPS (TLS 1.2 and 1.3 only) |
| 80 | Only redirects to HTTPS with a `301` |

Every other service (frontend, backend, PostgreSQL, Elasticsearch, Kibana) is reachable
only inside the Docker networks. TLS ends here: traffic between Nginx and the services
travels over the internal network.

## Routes

| Path | Upstream | Notes |
|------|----------|-------|
| `/api/v1/auth/login` | `backend:3001` | 5 requests/min per IP, the 6th gets a `429` |
| `/api/` | `backend:3001` | REST API and Swagger (`/api/docs`), 20 requests/s per IP |
| `/socket.io/` | `backend:3001` | WebSocket upgrade, 1 h idle timeout |
| `/kibana/` | `kibana:5601` | Kibana login |
| `/` | `frontend:3000` | React app |
| `/healthz` | — | Returns `200 ok`, used by the container healthcheck |

Upstreams are resolved at request time through Docker's DNS, so Nginx starts even if a
service is missing; requests to that service get a `502`.

## SSL certificate

On the first start, `10-self-signed-cert.sh` creates a self-signed certificate for
`$DOMAIN` (default `localhost`) in the `nginx_certs` volume:

- `/etc/nginx/ssl/fullchain.pem`: certificate, valid for 365 days
- `/etc/nginx/ssl/privkey.pem`: private key, readable by root only

The script runs from `/docker-entrypoint.d/`, which the official image executes before
Nginx starts. If both files already exist it does nothing, so the certificate survives
restarts. In production (VPS) a Let's Encrypt certificate is mounted at the same paths
and the script skips the generation.

The browser shows a warning with the self-signed certificate: this is expected in
development and evaluation. Certificates and keys are never committed (`.gitignore`).

To create a new certificate, remove the volume:

```bash
docker compose -f docker-compose.dev.yml down
docker volume rm sentinel-dev_nginx_certs
```

## Security headers

Added to every HTTPS response, including errors:

| Header | Value |
|--------|-------|
| `Content-Security-Policy` | `default-src 'self'; connect-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; font-src 'self'; frame-ancestors 'none'` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |

`Strict-Transport-Security` is added only in production: with a self-signed certificate
it would lock the browser out of `localhost`.

Nginx overwrites `X-Forwarded-For` and `X-Real-IP` with the real client address, so a
client cannot spoof its IP to the backend by sending those headers.

## Check it

```bash
curl -sI http://localhost                 # 301 → https://localhost/
curl -skI https://localhost/healthz       # 200 and the security headers
openssl s_client -connect localhost:443 -tls1_1 </dev/null   # handshake fails
```
