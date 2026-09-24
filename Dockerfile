FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        python3-pip \
        ca-certificates \
        curl \
        gnupg \
        rclone && \
    curl -fsSL https://apt.corretto.aws/corretto.key \
        | gpg --dearmor -o /usr/share/keyrings/corretto-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/corretto-keyring.gpg] https://apt.corretto.aws stable main" \
        > /etc/apt/sources.list.d/corretto.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        java-25-amazon-corretto-jdk && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/stemcraft-console

COPY requirements.txt .
RUN python3 -m venv .venv && \
    .venv/bin/pip install --upgrade pip && \
    .venv/bin/pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .

RUN mkdir -p \
    /var/lib/stemcraft-console \
    /srv/minecraft \
    /etc/stemcraft-console

ENV STEMCRAFT_CONSOLE_HOST=0.0.0.0
ENV STEMCRAFT_CONSOLE_PORT=8000
ENV STEMCRAFT_CONSOLE_DATABASE=/var/lib/stemcraft-console/stemcraft-console.db
ENV STEMCRAFT_CONSOLE_SERVER_ROOT=/srv/minecraft

EXPOSE 8000
EXPOSE 25565-25600

CMD ["/bin/bash", "-c", "\
    .venv/bin/python -c 'from app.migrations import upgrade_database; upgrade_database()' && \
    PASSWORD=$(.venv/bin/python -m app.admin_cli ensure-admin --username admin) && \
    if [ -n \"$PASSWORD\" ]; then \
      echo '============================================'; \
      echo 'STEMCraft Console initial administrator'; \
      echo 'Username: admin'; \
      echo \"Temporary password: $PASSWORD\"; \
      echo '============================================'; \
    fi && \
    exec .venv/bin/python -m app.run \
"]