FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    cups-client \
    supervisor \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
# Default-Templates (.j2) in ein separates Verzeichnis im Image legen,
# damit sie nicht durch das Volume-Mount überschrieben werden und
# niemals vom Jinja2-UI-Loader gefunden werden koennen.
COPY templates/ templates_default/
COPY supervisord.conf /etc/supervisor/conf.d/mail2print.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p /app/data /app/logs /app/templates

EXPOSE 635

CMD ["/entrypoint.sh"]
