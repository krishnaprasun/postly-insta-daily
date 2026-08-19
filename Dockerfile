FROM python:3.11-slim

# Devanagari shaping needs BOTH a Devanagari face and raqm (Pillow's wheel bundles
# raqm, libraqm0 is belt-and-braces). Without them every variant fails by design,
# so the build below asserts it rather than letting the service start broken.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libraqm0 fonts-noto-core fonts-indic \
    && rm -rf /var/lib/apt/lists/*

# DEVANAGARI_FONT is deliberately unset: hinditext searches the font tree and
# picks a bold Devanagari face, so differing package filenames still work.
# DATA_DIR is left at its in-image default: generated JPEGs and the run database
# are EPHEMERAL by design. The post is reviewed and downloaded the same morning,
# so nothing here needs to outlive the container.
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Fail the BUILD if Devanagari cannot be shaped — finding out at generation time
# costs a day's post and a confusing debug session.
RUN python -c "import imaging, sys; ok = imaging.shaping_available(); \
    print('[build] devanagari shaping:', ok); sys.exit(0 if ok else 1)"

EXPOSE 8000
CMD ["gunicorn", "-w", "1", "-t", "600", "-b", "0.0.0.0:8000", "app:app"]
