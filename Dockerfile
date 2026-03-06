FROM python:3.12-slim

# CUPS-Client-Tools und supervisord installieren
RUN apt-get update && apt-get install -y --no-install-recommends \
    cups-client \
    supervisor \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY templates/ templates/
COPY supervisord.conf /etc/supervisor/conf.d/mail2print.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Laufzeit-Verzeichnisse anlegen
RUN mkdir -p /app/data /app/logs

# WebUI-Port
EXPOSE 635

CMD ["/entrypoint.sh"]
