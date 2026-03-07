FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[all]"

# Copy application code
COPY . .

# Default environment
ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8080
ENV LOG_LEVEL=INFO

# Document storage directory
RUN mkdir -p /data/documents
ENV MCP_DOCUMENTS_DIR=/data/documents

EXPOSE 8080

CMD ["python", "server.py"]
