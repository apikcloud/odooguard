FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y wget gnupg ca-certificates && \
    echo "deb http://apt.postgresql.org/pub/repos/apt/ bookworm-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list && \
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        | gpg --dearmor -o /etc/apt/trusted.gpg.d/pgdg.gpg && \
    apt-get update && \
    apt-get install -y postgresql-client-18 \
                      python3 \
                      python3-pip \
                      cron \
                      tzdata \
                      locales \
                      zip && \
    rm -rf /var/lib/apt/lists/*

# Generate fr_FR.UTF-8 to allow docker-compose to set LANG/LC_ALL
RUN sed -i 's/# fr_FR.UTF-8 UTF-8/fr_FR.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen

# IMPORTANT: do NOT force C.UTF-8 here: docker-compose must override LANG/LC_ALL
# ENV LANG=C.UTF-8
# ENV LC_ALL=C.UTF-8

WORKDIR /app

COPY backup.py /app/backup.py
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh /app/backup.py

# Defaults (overridable)
ENV CRON_SCHEDULE="0 2 * * *" \
    PGHOST=postgres \
    PGUSER=odoo \
    PGPASSWORD=odoo \
    PGPORT=5432 \
    ODOO_CONF=/etc/odoo/odoo.conf \
    DB_NAME=""

ENTRYPOINT ["/entrypoint.sh"]
