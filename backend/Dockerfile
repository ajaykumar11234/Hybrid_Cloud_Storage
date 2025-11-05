# Use a full Python image instead of slim to ensure SSL support
FROM python:3.11-slim

WORKDIR /app

# Install libmagic + CA certificates for SSL verification
RUN apt-get update && \
    apt-get install -y libmagic1 ca-certificates && \
    update-ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY backend /app

EXPOSE 8000

CMD ["python", "app.py"]
