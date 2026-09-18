# Legal Rent AI API — Python 3.11, FastAPI, pyodbc/SQL Server, document + LLM stack (in-process AI).
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend \
    LEGAL_CAG_CORPUS_PATH=docs/legal-sources/cag-corpus-v1.md

WORKDIR /app

# System: ODBC 18 (pyodbc), PDF/DOCX (wheels + Pillow), Tesseract (pytesseract; OCR stub today).
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg2 \
    apt-transport-https \
    unixodbc \
    unixodbc-dev \
    tesseract-ocr \
    tesseract-ocr-spa \
    libjpeg62-turbo \
    zlib1g \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/microsoft-prod.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY backend ./backend
COPY docs/legal-sources/cag-corpus-v1.md ./docs/legal-sources/cag-corpus-v1.md

# Core deps only — optional [rag] (chromadb/torch) is not used by the MVP API.
RUN pip install --upgrade "pip<26" && pip install . "python-multipart>=0.0.6"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
