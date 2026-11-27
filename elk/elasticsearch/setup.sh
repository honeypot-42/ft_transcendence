#!/bin/sh
# One-shot ELK setup, run by the `elk-setup` service; the container then exits.
#  - ILM policy, component template and index templates for the data streams
#  - least-privilege roles and users for Logstash and the backend
#  - kibana_system password (only if KIBANA_SYSTEM_PASSWORD is set)
# Idempotent: every call is a PUT/POST that overwrites, so it is safe to run
# on every `docker compose up`. Any failed request stops the script with a
# non-zero exit code, and the services that depend on it do not start.
set -eu

ES="http://elasticsearch:9200"
AUTH="elastic:${ELASTIC_PASSWORD}"
DIR=/setup

fail() {
  echo "[elk-setup] ERROR: $1" >&2
  exit 1
}

# Passwords are written inside JSON bodies below. Allowing only these
# characters means a value can never break the JSON or inject extra fields.
# `openssl rand -hex 32` always matches.
check_secret() { # name value
  case "$2" in
    '' | *[!A-Za-z0-9_-]*) fail "$1 is empty or has characters other than A-Z a-z 0-9 _ -" ;;
  esac
}
check_secret ELASTIC_PASSWORD "$ELASTIC_PASSWORD"
check_secret LOGSTASH_ES_USER "$LOGSTASH_ES_USER"
check_secret LOGSTASH_ES_PASSWORD "$LOGSTASH_ES_PASSWORD"
check_secret BACKEND_ES_USER "$BACKEND_ES_USER"
check_secret BACKEND_ES_PASSWORD "$BACKEND_ES_PASSWORD"
if [ -n "${KIBANA_SYSTEM_PASSWORD:-}" ]; then
  check_secret KIBANA_SYSTEM_PASSWORD "$KIBANA_SYSTEM_PASSWORD"
fi

req() { # method path json-file
  curl -fsS -u "$AUTH" -X "$1" "$ES$2" \
    -H 'Content-Type: application/json' --data-binary "@$3" >/dev/null
  echo "[elk-setup] $1 $2 OK"
}

json() { # method path inline-json
  curl -fsS -u "$AUTH" -X "$1" "$ES$2" \
    -H 'Content-Type: application/json' -d "$3" >/dev/null
  echo "[elk-setup] $1 $2 OK"
}

# Compose already waits for the healthcheck; this also catches a wrong password
# instead of hanging forever (40 attempts x 3 s = 2 min).
echo "[elk-setup] Waiting for Elasticsearch..."
attempt=0
until curl -fsS -u "$AUTH" "$ES/_cluster/health?wait_for_status=yellow&timeout=5s" >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  [ "$attempt" -ge 40 ] && fail "Elasticsearch not reachable or ELASTIC_PASSWORD is wrong"
  sleep 3
done

# ─── Retention: 90 days (ILM) ────────────────────────────────────────────────
req PUT /_ilm/policy/sentinel-logs             "$DIR/ilm-policy.json"
req PUT /_component_template/sentinel-settings "$DIR/component-settings.json"
req PUT /_index_template/logs-honeypot         "$DIR/template-honeypot.json"
req PUT /_index_template/logs-app              "$DIR/template-app.json"

# ─── Roles ───────────────────────────────────────────────────────────────────
# Logstash only appends documents. Templates and ILM are created above by this
# script, so it needs no cluster privilege to manage them.
json PUT /_security/role/logstash_writer '{
  "cluster": ["monitor"],
  "indices": [{
    "names": ["logs-honeypot-*", "logs-app-*"],
    "privileges": ["create_doc", "auto_configure", "view_index_metadata"]
  }]
}'

# The backend only reads.
json PUT /_security/role/sentinel_reader '{
  "cluster": ["monitor"],
  "indices": [{
    "names": ["logs-honeypot-*", "logs-app-*"],
    "privileges": ["read", "view_index_metadata"]
  }]
}'

# ─── Users ───────────────────────────────────────────────────────────────────
json PUT "/_security/user/${LOGSTASH_ES_USER}" "{
  \"password\": \"${LOGSTASH_ES_PASSWORD}\",
  \"roles\": [\"logstash_writer\"]
}"

json PUT "/_security/user/${BACKEND_ES_USER}" "{
  \"password\": \"${BACKEND_ES_PASSWORD}\",
  \"roles\": [\"sentinel_reader\"]
}"

if [ -n "${KIBANA_SYSTEM_PASSWORD:-}" ]; then
  json POST /_security/user/kibana_system/_password "{\"password\": \"${KIBANA_SYSTEM_PASSWORD}\"}"
fi

echo "[elk-setup] Done"
