FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libmagic1 && apt-get clean

# 👇 FIX: specify the correct path
COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# 👇 FIX: copy everything inside backend/
COPY backend /app

EXPOSE 8000

CMD ["python", "app.py"]
