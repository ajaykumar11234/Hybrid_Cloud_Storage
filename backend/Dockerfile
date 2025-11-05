FROM python:3.11-bullseye

WORKDIR /app

RUN apt-get update && \
    apt-get install -y libmagic1 ca-certificates openssl && \
    update-ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app

EXPOSE 8000

CMD ["python", "app.py"]
