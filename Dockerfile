FROM python:3.12-slim

# Install CUPS client tools and supervisord
RUN apt-get update && apt-get install -y --no-install-recommends \
    cups-client \
    supervisor \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY templates/ templates/
COPY supervisord.conf /etc/supervisor/conf.d/email2print.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Ensure runtime directories exist
RUN mkdir -p /app/data /app/logs

# WebUI port
EXPOSE 635

CMD ["/entrypoint.sh"]
