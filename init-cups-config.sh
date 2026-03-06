#!/bin/sh
# ══════════════════════════════════════════════════════════════════════════════
# init-cups-config.sh
#
# Wird einmalig vom cups-init-Container ausgeführt.
# Kopiert alle CUPS-Standard-Konfigurationsdateien und -Verzeichnisse
# aus dem Container-Image in das gemountete ./cups/-Verzeichnis auf dem Host,
# sofern sie dort noch nicht vorhanden sind.
#
# Folgende Dateien werden kopiert (falls nicht vorhanden):
#   classes.conf, cups-browsed.conf, cups-files.conf, cups-pdf.conf,
#   cupsd.conf, printers.conf, snmp.conf, raw.convs, raw.types,
#   tea4cups.conf
#
# Folgende Verzeichnisse werden angelegt (falls nicht vorhanden):
#   interfaces/, ppd/, ssl/
# ══════════════════════════════════════════════════════════════════════════════

set -e

SRC="/etc/cups"
DST="/etc/cups"

# Sicherstellen, dass das Zielverzeichnis existiert
mkdir -p "${DST}"

echo "[cups-init] Prüfe CUPS-Konfigurationsdateien in ${DST} ..."

# Konfigurationsdateien: nur kopieren wenn noch nicht vorhanden
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

    if [ ! -f "${DST}/${FILE}" ]; then
        if [ -f "${SRC}/${FILE}" ]; then
            cp "${SRC}/${FILE}" "${DST}/${FILE}"
            echo "[cups-init] Kopiert: ${FILE}"
        else
            echo "[cups-init] Nicht im Image vorhanden (übersprungen): ${FILE}"
        fi
    else
        echo "[cups-init] Bereits vorhanden (übersprungen): ${FILE}"
    fi
done

# Verzeichnisse anlegen falls nicht vorhanden
for DIR in interfaces ppd ssl; do
    if [ ! -d "${DST}/${DIR}" ]; then
        if [ -d "${SRC}/${DIR}" ]; then
            cp -r "${SRC}/${DIR}" "${DST}/${DIR}"
            echo "[cups-init] Verzeichnis kopiert: ${DIR}/"
        else
            mkdir -p "${DST}/${DIR}"
            echo "[cups-init] Verzeichnis angelegt (leer): ${DIR}/"
        fi
    else
        echo "[cups-init] Verzeichnis bereits vorhanden (übersprungen): ${DIR}/"
    fi
done

echo "[cups-init] Initialisierung abgeschlossen."
