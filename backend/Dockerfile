# backend/Dockerfile
FROM python:3.11-bullseye

WORKDIR /app

# Install system packages (ClamAV, libmagic, openssl, gettext for tesseract if needed)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libmagic1 \
      ca-certificates \
      openssl \
      clamav \
      clamav-daemon \
      clamdscan \
      tesseract-ocr \
      tesseract-ocr-eng \
      && update-ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY backend /app

# Add entrypoint
COPY backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

# Entrypoint will start freshclam, clamd, then gunicorn
CMD ["/entrypoint.sh"]
