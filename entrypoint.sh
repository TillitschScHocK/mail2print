#!/bin/sh
# Entrypoint: write /etc/cups/client.conf so the lp/lpstat client connects
# to the correct CUPS server with the right IPP version.
#
# The 'add /version=1.1 to server name' error occurs when a CUPS 1.x client
# talks to a CUPS 2.x server without explicitly negotiating the IPP version.
# Writing ServerName with /version=1.1 fixes this permanently for all tools
# (lp, lpstat, lpoptions, etc.) without patching every command line.

set -e

mkdir -p /etc/cups

if [ -n "${CUPS_SERVER}" ]; then
    SERVER="${CUPS_SERVER}"
    # Append /version=1.1 if not already present
    case "${SERVER}" in
        */version=*) ;;
        *) SERVER="${SERVER}/version=1.1" ;;
    esac

    echo "ServerName ${SERVER}" > /etc/cups/client.conf
    echo "[entrypoint] CUPS client configured: ServerName ${SERVER}"
else
    echo "[entrypoint] CUPS_SERVER not set, using default CUPS client config."
fi

exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/email2print.conf
