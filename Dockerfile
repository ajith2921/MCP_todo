FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY database.py .
COPY server.py .
COPY app.py .
COPY cli.py .

# Expose port (default 8000, overridden by Railway/Render via $PORT)
ENV PORT=8000
EXPOSE 8000

# Start MCP Server in SSE mode
CMD python server.py --transport sse --host 0.0.0.0 --port ${PORT}

