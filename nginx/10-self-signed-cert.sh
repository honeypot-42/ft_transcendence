#!/bin/sh
# Creates a self-signed certificate for local development and evaluation.
# The official image runs every script in /docker-entrypoint.d/ before Nginx
# starts. The certificate lives in the nginx_certs volume, never in the repo.
# In production (VPS) a Let's Encrypt certificate is mounted instead and this
# script does nothing.
set -eu

CERT_DIR=/etc/nginx/ssl
CERT="$CERT_DIR/fullchain.pem"
KEY="$CERT_DIR/privkey.pem"
DOMAIN="${DOMAIN:-localhost}"

if [ -s "$CERT" ] && [ -s "$KEY" ]; then
  echo "[ssl] Certificate found, skipping generation"
  exit 0
fi

mkdir -p "$CERT_DIR"
echo "[ssl] Generating self-signed certificate for $DOMAIN"
# Restrictive umask: the private key is created readable by root only
(
  umask 077
  openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
    -keyout "$KEY" -out "$CERT" \
    -subj "/CN=$DOMAIN" \
    -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost,IP:127.0.0.1" >/dev/null 2>&1
)
chmod 644 "$CERT"
