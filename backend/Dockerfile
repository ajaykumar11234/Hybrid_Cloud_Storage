# ======================================================
# 🧠 Base Image
# ======================================================
FROM python:3.11-slim

# ======================================================
# 📦 Install System Dependencies
# ======================================================
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libmagic1 \
        tesseract-ocr \
        tesseract-ocr-eng \
        poppler-utils \
        ffmpeg \
        tini \
        ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ======================================================
# ⚙️ Setup Environment
# ======================================================
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# ======================================================
# 📦 Install Python Dependencies
# ======================================================
# Copy requirements.txt from backend folder into container
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# ======================================================
# 📁 Copy Application Code
# ======================================================
COPY . /app

# ======================================================
# 🚀 Entrypoint
# ======================================================
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]
