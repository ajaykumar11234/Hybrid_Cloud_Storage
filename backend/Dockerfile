# ======================================================
# 🧠 Base Image
# ======================================================
FROM python:3.11-slim

# ======================================================
# 📦 Install Only Essential System Dependencies
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
# ⚙️ Setup Workdir and Environment
# ======================================================
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# ======================================================
# 📦 Install Python Dependencies
# ======================================================
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ======================================================
# 🧩 Copy Project Files
# ======================================================
COPY . .

# ======================================================
# 🚀 Entrypoint
# ======================================================
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]
