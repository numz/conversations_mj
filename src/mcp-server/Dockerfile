FROM python:3.12-slim

WORKDIR /app

# Copy application code and install dependencies
COPY . .
RUN pip install --no-cache-dir ".[all]"

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
