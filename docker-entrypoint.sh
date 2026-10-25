#!/bin/sh
set -e

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

mkdir -p /data/music /app/temp

# Bind mounts use host ownership; fix when we start as root (default in compose).
if [ "$(id -u)" = "0" ]; then
    chown -R "${PUID}:${PGID}" /data/music /app/temp
    exec gosu "${PUID}:${PGID}" "$@"
fi

exec "$@"
