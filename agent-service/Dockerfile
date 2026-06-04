FROM python:3.11-slim

WORKDIR /app

# System deps (graphviz is in requirements but optional; keep slim)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY agent_service.py .

# Cloud Run injects PORT; default to 8000 locally
ENV PORT=8000
EXPOSE 8000

# Run with uvicorn directly so we can use $PORT properly
CMD exec uvicorn agent_service:app --host 0.0.0.0 --port ${PORT}
