# ======================================================
# 🧠 Base Image
# ======================================================
FROM python:3.11-slim

# ======================================================
# 📦 System Dependencies
# ======================================================
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libmagic1 \
        tesseract-ocr \
        tesseract-ocr-eng \
        poppler-utils \
        ffmpeg \
        curl \
        tini \
        ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ======================================================
# 🏗️ Environment Setup
# ======================================================
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# ======================================================
# 🔧 Copy Dependencies
# ======================================================
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# ======================================================
# 📁 Copy Source Code
# ======================================================
COPY . /app

# ======================================================
# 🚀 Entrypoint
# ======================================================
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]
