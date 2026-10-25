#!/bin/sh
set -e

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"
MUSIC_DIR="${MUSIC_LIBRARY_PATH:-/data/music}"
SCRATCH_DIR="${TEMP_DIR:-/app/temp}"

mkdir -p "$MUSIC_DIR" "$SCRATCH_DIR"

# Bind mounts use host ownership; fix when we start as root (default in compose).
if [ "$(id -u)" = "0" ]; then
    chown -R "${PUID}:${PGID}" "$MUSIC_DIR" "$SCRATCH_DIR"
    exec gosu "${PUID}:${PGID}" "$@"
fi

exec "$@"
