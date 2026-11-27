# Headers sent to every upstream. Included from each proxied location.
# The .inc extension keeps it out of the "conf.d/*.conf" include in nginx.conf.
proxy_http_version 1.1;
proxy_set_header Host              $host;
# Overwrite (never append) the client IP: whatever the client sends in
# X-Forwarded-For is discarded, so it cannot spoof its address to the backend.
proxy_set_header X-Real-IP         $remote_addr;
proxy_set_header X-Forwarded-For   $remote_addr;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header Upgrade           $http_upgrade;
proxy_set_header Connection        $connection_upgrade;
