# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if ClamAV client needed)
RUN apt-get update && apt-get install -y libmagic1 && apt-get clean

# Copy requirements
COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY backend /app/backend
COPY app.py config.py /app/

# Expose app port
EXPOSE 8000

# Start backend
CMD ["python", "app.py"]
