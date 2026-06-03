FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer for faster rebuilds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server code
COPY server.py .

# Cloud Run sets PORT env var; our server reads it
ENV PORT=8080
EXPOSE 8080

# Start the server
CMD ["python", "server.py"]
