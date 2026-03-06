#!/bin/sh
set -e

mkdir -p /etc/cups

if [ -n "${CUPS_SERVER}" ]; then
    SERVER="${CUPS_SERVER}"
    case "${SERVER}" in
        */version=*) ;;
        *) SERVER="${SERVER}/version=1.1" ;;
    esac
    echo "ServerName ${SERVER}" > /etc/cups/client.conf
    echo "[entrypoint] CUPS client configured: ServerName ${SERVER}"
else
    echo "[entrypoint] CUPS_SERVER not set, using default CUPS client config."
fi

mkdir -p /app/templates
for src in /app/templates_default/*.j2 /app/templates_default/*.txt; do
    [ -f "$src" ] || continue
    fname="$(basename "$src")"
    if [ ! -f "/app/templates/$fname" ]; then
        cp "$src" "/app/templates/$fname"
        echo "[entrypoint] Installed default template: $fname"
    fi
done

exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/mail2print.conf
