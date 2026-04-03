FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# ── Instalar PyTorch CPU-only primero desde el índice oficial de PyTorch ──────
# Esto evita descargar la versión CUDA (+670 MB) desde PyPI.
# Se instala con --timeout alto y --retries para redes lentas.
RUN pip install --no-cache-dir \
    --timeout 120 \
    --retries 5 \
    torch==2.1.1+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# ── Resto de dependencias desde PyPI ─────────────────────────────────────────
RUN pip install --no-cache-dir \
    --timeout 120 \
    --retries 5 \
    fastapi==0.104.1 \
    "uvicorn[standard]==0.24.0" \
    "transformers==4.35.2" \
    kafka-python==2.0.2 \
    "numpy==1.26.2" \
    prometheus-client==0.19.0

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
