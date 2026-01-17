# Multi-stage build for PQC Secure Transfer System
FROM python:3.11-slim as builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Try to install liboqs-python (may fail on some architectures)
RUN pip install liboqs-python || echo "liboqs-python not available for this architecture"

# Production stage
FROM python:3.11-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libssl3 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r pqcuser && useradd -r -g pqcuser pqcuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY pqc_secure_transfer/ ./pqc_secure_transfer/
COPY examples/ ./examples/
COPY simple_demo.py test_system.py ./
COPY README.md LICENSE CHANGELOG.md ./

# Create directories for keys and received files
RUN mkdir -p /app/keys /app/received_files && \
    chown -R pqcuser:pqcuser /app

# Switch to non-root user
USER pqcuser

# Expose port for server
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import pqc_secure_transfer; print('OK')" || exit 1

# Default command
CMD ["python", "examples/server.py", "--host", "0.0.0.0", "--port", "8765"]

# Labels for metadata
LABEL maintainer="PQC Secure Transfer Team" \
      version="1.0.0" \
      description="Post-Quantum Cryptography secure data transfer system" \
      org.opencontainers.image.title="PQC Secure Transfer" \
      org.opencontainers.image.description="Quantum-resistant secure file transfer for federated learning" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="PQC Secure Transfer Project" \
      org.opencontainers.image.licenses="MIT"