FROM python:3.11-slim

# libraqm + a Devanagari font: without BOTH, Pillow cannot shape Hindi conjuncts
# and every variant fails by design (see gen.py). Verified at /healthz after deploy.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libraqm0 fonts-noto-devanagari fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

ENV DEVANAGARI_FONT=/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Surface shaping status at build time — a green build with a red line here means
# the image will start but refuse to generate.
RUN python -c "import imaging; print('[build] devanagari shaping:', imaging.shaping_available())" || true

EXPOSE 8000
CMD ["gunicorn", "-w", "1", "-t", "600", "-b", "0.0.0.0:8000", "app:app"]
