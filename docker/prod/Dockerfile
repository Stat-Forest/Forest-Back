FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install PostgreSQL 16 client and required system dependencies
RUN apt-get update && \
    apt-get install -y curl gnupg build-essential libpq-dev gcc netcat-openbsd zip && \
    echo "deb http://apt.postgresql.org/pub/repos/apt/ $(grep VERSION_CODENAME /etc/os-release | cut -d= -f2)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/pgdg.gpg && \
    apt-get update && \
    apt-get install -y postgresql-client-16 && \
    rm -rf /var/lib/apt/lists/*

# Copy entrypoint script
COPY docker/prod/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Install Python dependencies
COPY requirements/ /app/requirements/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements/prod.txt

# Copy project source
COPY src /app

# Konteyner root'da ishlamaydi (audit B14). Bind-mount qilingan papkalar (src,
# media, staticfiles, backups, /var/log/forest-back, .env) va MIB kaliti
# (keys/mib) deploy skriptida shu UID'ga chown qilinadi (deploy.yml).
RUN useradd --system --uid 1000 --create-home app \
    && mkdir -p /var/log/forest-back /app/media /app/staticfiles /backups \
    && chown -R app:app /app /var/log/forest-back /backups
USER app
