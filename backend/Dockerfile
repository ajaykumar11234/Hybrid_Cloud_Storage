# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Optional: install ClamAV client library dependencies
RUN apt-get update && apt-get install -y libmagic1 && apt-get clean

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything inside backend/
COPY . .

# Expose app port
EXPOSE 8000

# Start backend
CMD ["python", "app.py"]
