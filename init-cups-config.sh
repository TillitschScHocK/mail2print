#!/bin/sh
# ══════════════════════════════════════════════════════════════════════════════
# init-cups-config.sh
#
# Wird einmalig vom cups-init-Container ausgeführt.
# Da das drpsychick/airprint-bridge-Image die CUPS-Configs erst beim Start
# von cupsd generiert, wird cupsd hier kurz im Hintergrund gestartet,
# gewartet bis die Dateien vorhanden sind, und dann gestoppt.
# Anschließend werden alle Configs in das gemountete ./cups/-Verzeichnis
# kopiert – jedoch nur, wenn sie dort noch NICHT vorhanden sind.
# ══════════════════════════════════════════════════════════════════════════════

set -e

MOUNT="/mnt/cups-config"
CUPS_ETC="/etc/cups"

echo "[cups-init] Starte cupsd einmalig zur Konfig-Generierung ..."

# cupsd kurz im Hintergrund starten (ohne Mount, generiert Configs in /etc/cups)
/usr/sbin/cupsd -f &
CUPSD_PID=$!

# Warten bis cupsd.conf vorhanden ist (max. 15 Sekunden)
WAIT=0
until [ -f "${CUPS_ETC}/cupsd.conf" ] || [ "$WAIT" -ge 15 ]; do
    sleep 1
    WAIT=$((WAIT + 1))
done

# cupsd sauber beenden
kill "$CUPSD_PID" 2>/dev/null || true
sleep 1

if [ ! -f "${CUPS_ETC}/cupsd.conf" ]; then
    echo "[cups-init] FEHLER: cupsd.conf wurde nicht generiert. Breche ab."
    exit 1
fi

echo "[cups-init] Configs generiert. Kopiere in ${MOUNT} ..."
mkdir -p "${MOUNT}"

# Konfigurationsdateien: nur kopieren wenn im Mount noch nicht vorhanden
for FILE in \
    classes.conf \
    cups-browsed.conf \
    cups-files.conf \
    cups-pdf.conf \
    cupsd.conf \
    printers.conf \
    snmp.conf \
    raw.convs \
    raw.types \
    tea4cups.conf; do

    if [ ! -f "${MOUNT}/${FILE}" ]; then
        if [ -f "${CUPS_ETC}/${FILE}" ]; then
            cp "${CUPS_ETC}/${FILE}" "${MOUNT}/${FILE}"
            echo "[cups-init] Kopiert: ${FILE}"
        else
            echo "[cups-init] Nicht vorhanden (übersprungen): ${FILE}"
        fi
    else
        echo "[cups-init] Bereits vorhanden (übersprungen): ${FILE}"
    fi
done

# Verzeichnisse kopieren oder anlegen
for DIR in interfaces ppd ssl; do
    if [ ! -d "${MOUNT}/${DIR}" ]; then
        if [ -d "${CUPS_ETC}/${DIR}" ]; then
            cp -r "${CUPS_ETC}/${DIR}" "${MOUNT}/${DIR}"
            echo "[cups-init] Verzeichnis kopiert: ${DIR}/"
        else
            mkdir -p "${MOUNT}/${DIR}"
            echo "[cups-init] Verzeichnis angelegt (leer): ${DIR}/"
        fi
    else
        echo "[cups-init] Verzeichnis bereits vorhanden (übersprungen): ${DIR}/"
    fi
done

echo "[cups-init] Initialisierung abgeschlossen."
