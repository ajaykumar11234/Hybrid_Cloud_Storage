# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app
COPY . .

# Install dependencies
RUN apt-get update && apt-get install -y clamav clamav-daemon && \
    pip install --no-cache-dir -r requirements.txt

# Update virus database
RUN freshclam

# Copy ClamAV config if needed (optional)
# COPY config/clamd.conf /etc/clamav/clamd.conf

# Expose Flask and ClamD ports
EXPOSE 5000 3310

# Start both ClamD and Flask app
CMD service clamav-daemon start && python app.py
