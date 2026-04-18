FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including audio tools
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Piper TTS (optional — will download on first use if not cached)
# For offline/Docker builds, pre-cache the voice model:
# Docker build --build-arg PIPER_VOICE=en_US-amy-medium ...
ARG PIPER_VOICE=en_US-amy-medium
RUN curl -sSL https://github.com/rhasspy/piper/releases/download/2024.08.01/piper_linux_x86_64.tar.gz \
    | tar xzf - -C /usr/local/bin && \
    chmod +x /usr/local/bin/piper

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 spectra && chown -R spectra:spectra /app
USER spectra

# Health check (stdlib only — no extra deps)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
