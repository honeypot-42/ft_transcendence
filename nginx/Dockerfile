# Nginx — single entry point of the application (HTTPS only).
FROM nginx:1.30-alpine

# openssl is only needed to create the self-signed certificate on first start.
# Not pinned: Alpine removes old package versions from its mirrors, so a pinned
# version would break the build; security fixes come with every rebuild.
# hadolint ignore=DL3018
RUN apk add --no-cache openssl

COPY --chmod=755 10-self-signed-cert.sh /docker-entrypoint.d/10-self-signed-cert.sh

RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/

EXPOSE 80 443

HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD ["wget", "-q", "--no-check-certificate", "-O", "/dev/null", "https://127.0.0.1/healthz"]
