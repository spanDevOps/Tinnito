FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directories with proper permissions
RUN mkdir -p mpthrees logs && \
    chown -R nobody:nogroup mpthrees logs && \
    chmod 755 mpthrees logs

# Copy gunicorn config
COPY gunicorn.conf.py .

# Copy application code
COPY . .

# Set non-root user
USER nobody

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start the application with production settings
CMD ["gunicorn", "--config", "gunicorn.conf.py", "url_server:app"]
